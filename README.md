# ASD-STE100-inspired clarity skill

A meaning-preserving editor for a selected passage of technical English. This repository is a fork of [mikeqwe/asd-ste100-skill](https://github.com/mikeqwe/asd-ste100-skill), which is itself a fork of [danyuchn/asd-ste100-skill](https://github.com/danyuchn/asd-ste100-skill). It is not an official ASD tool or a demonstrated agent-reliability improvement.

The goal is easier reading without changing facts, uncertainty, requirements, or behavior. Use it for an explicit editing task, not as a global style mandate. The core instruction is in [SKILL.md](SKILL.md).

## What changes in 0.6.0

Version 0.6.0 adds `scripts/ste-preserve.py`, a read-only check that compares a source with its rewrite. It lists modality, hedges, frequency words, negation, quantifiers, condition and contrast markers, numbers with units, code, and identifiers whose counts differ. It catches the most harmful rewrite failure, a hedge or a `should` that silently becomes a certainty or a `must`, when the changed word is on its lists: for example `may`, `should`, `will`, `possibly`, `unclear`, `we think`, or `about 30`. A hedge phrased some other way can still slip through.

The linter no longer lists `spin up` as a phrasal verb, because it is an established software term. Conversational idioms such as `reach out` and `circle back` are still listed.

Strict mode keeps technical compounds and jargon, and it falls back to STE-flavored edits for debugging hypotheses, design trade-offs, and decision records, with a `Strict not applied:` note. Contrasts and concessions join the list of meaning that a rewrite must preserve.

The skill sets `disable-model-invocation: true`, so it runs only when you invoke `/asd-ste100`.

## What changes in 0.5.0

The default is **STE-flavored**, even for prompts and tool descriptions. **Strict** remains available on explicit request, but meaning takes precedence over formal targets. Strict is not certification and does not change the linter's policy.

The skill now preserves recommendation strength as well as uncertainty, retains distinct technical operations, and flags unresolved ambiguity instead of choosing an interpretation. It does not add checks or guarantees to make incomplete instructions look complete. Already clear text is returned unchanged.

Examples no longer turn `should` into a command, add artifact validation, or infer data residency from "no vendor lock-in". See [before/after examples](examples/before-after.md).

The document-wide synonym detector has been removed: word membership cannot establish that two operations are equivalent. Terminology consistency remains an editorial check. Style hints are now advisory rather than build failures. Sentence-length hints join ordinary soft-wrapped prose and list continuations rather than checking each physical source line alone.

## Install for a local trial

From a test project's root, choose one destination:

```bash
# Claude Code
mkdir -p .claude/skills
git clone https://github.com/lysokine/asd-ste100-skill.git .claude/skills/asd-ste100

# Or Codex
mkdir -p .agents/skills
git clone https://github.com/lysokine/asd-ste100-skill.git .agents/skills/asd-ste100
```

For an unmerged PR, check out its head branch in that clone before trying it. Cloning the default branch does not include pending changes. Do not overwrite an existing installation. Check that the session loads this fork's `SKILL.md`, not another installed skill with the same name.

Use `/asd-ste100` in Claude Code or select the skill explicitly in Codex, then supply the text and ask to show the diff during the trial. Keep the source visible for comparison. The default output is just the rewritten text. A separate `Needs clarification:` note flags unresolved meaning, and a `Strict not applied:` note marks a passage where strict mode was declined.

Local skill locations are documented by [Claude Code](https://code.claude.com/docs/en/skills) and [Codex](https://developers.openai.com/codex/skills/). Native loading and model behavior must be checked in your own session; the Python tests below do not exercise either runtime.

## Optional linter

```bash
python3 scripts/ste-lint.py document.md
python3 scripts/ste-lint.py --json document.md
python3 scripts/ste-lint.py --baseline 1 document.md
python3 scripts/ste-lint.py --disable dangling-conjunction document.md
```

It reads stdin or files and never edits them. It needs only the Python standard library.

**Changed exit policy:** only `dangling-conjunction` findings contribute to `hard_count` and exit status 1 when they exceed `--baseline`. Semicolons, phrasal verbs, promotional wording, nominalization, passive voice, compound tenses, and length are review hints. The previous style-gating behavior is intentionally not preserved. Existing flags and JSON field names remain, including the legacy `violations` key. `--disable synonym-rotation` remains an accepted no-op.

A zero count is not evidence of truth, preserved meaning, or STE compliance. The linter cannot identify missing requirements, added facts, or changes in obligation. Do not rewrite text just to clear its hints.

### Parsing limits

This is a heuristic scanner, not a CommonMark or English parser. Length hints cover ordinary paragraphs, simple list continuations, and individual Markdown table cells; their location is the start of the containing block or cell. Blank lines, ATX headings, list items, tables, and fences separate blocks. Full nested-list semantics, blockquotes, abbreviations, and complex Markdown are not parsed reliably.

The incomplete-list check supports `-`, `*`, `+`, and numeric `.`/`)` markers with zero to three leading spaces and ASCII spaces after the marker. It examines indented continuations. Fenced code is skipped using the inherited three-backtick/three-tilde toggle; inline code is excluded from style checks. These limits are not a license to auto-fix findings.

## Meaning-marker check

```bash
python3 scripts/ste-preserve.py source.md rewrite.md
python3 scripts/ste-preserve.py --json source.md rewrite.md
```

Pass the rewritten text alone, without a `Needs clarification:` note. The check exits 0 when no marker differs, 1 when some differ, and 2 on a usage error. It reads both files and never edits them. It needs only the Python standard library.

Inflections share one item, so `requires` and `required` match, `three` matches `3`, and `30 seconds` matches `30 s`. Code spans, fenced blocks, URLs, and identifiers such as `--no-cache`, `CUDA_VISIBLE_DEVICES`, or `H100` are compared verbatim apart from trailing whitespace and sentence punctuation, and they are excluded from the word checks. Backticks count as formatting, so a flag with or without backticks is the same item.

Each listed difference is a question for the reviewer, since changing `once` to `if` can be correct. A clean result does not prove that the meaning is preserved, because the check counts markers and cannot read scope or intent.

## Verification and usefulness

```bash
python3 scripts/ste-lint.py --selftest
python3 scripts/ste-preserve.py --selftest
python3 -m unittest discover -s tests -v
```

The intentionally invalid [list fixture](examples/linter-edge-cases.md) should still produce two hard findings. Automated tests cover linter behavior and compatibility, not semantic preservation by a model.

[Manual rewrite cases](tests/rewrite-cases.md) compare the upstream skill, a short clarity instruction, and this fork. Check facts, logical scope, modality, actions, and costs before preferring an alternative. No native model A/B results are claimed for this version.

## Source and license

This skill borrows clarity principles from ASD-STE100; it does not include the official dictionary. See [the reference and boundaries](references/writing-rules.md) and [ASD's official site](https://www.asd-ste100.org/). Technical terms, necessary tense distinctions, and meaningful qualifications take precedence over this adaptation's style targets.

MIT — see [LICENSE](LICENSE).
