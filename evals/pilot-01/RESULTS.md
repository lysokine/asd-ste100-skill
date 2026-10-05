# Pilot 01: skill vs short instruction vs plain request

Run on 2026-10-05 with skill version 0.7.0. One run per arm, five passages. Treat it as a pilot, not evidence.

## Method

1. Five passages adapted from the repository owner's own agent rules and cluster notes (`passages.json`). Names, paths, IDs, and project details were removed; the wording was otherwise kept, including its hedges and its fragments.
2. 23 reader questions with expected answers (`questions.json`), written from the source and committed before any rewrite existed.
3. Three arms, each run once by a fresh Claude Opus 5.5 agent that saw only its own instruction (`outputs/arm_*.json`):
   - A: read `SKILL.md` and apply it in its default mode.
   - B: the one-line short instruction from `tests/rewrite-cases.md`.
   - C: "Rewrite each of the five passages below for clarity."
4. Readback: a Claude Fable 5.1 agent got the original and the three rewrites of each passage under shuffled labels (`blind_key.json`). It answered every question from each version alone, then ranked the versions from easiest to hardest to act on (`outputs/readback_fable.json`).
5. Scoring: Codex (gpt-6-astra, medium effort), also blind to the labels, graded each answer against the expected answer (`outputs/scoring_codex.json`).
6. `scripts/ste-preserve.py` compared each rewrite with its source (`outputs/checker_results.json`).

## Results

| | Original | A: skill | B: short instruction | C: plain request |
|---|---:|---:|---:|---:|
| Readback answers graded correct (of 23) | 22 | 22 | 22 | 22 |
| Mean readability rank (1 = easiest, of 4) | 4.0 | 2.8 | 2.0 | 1.2 |
| Passages with checker differences (of 5) | – | 0 | 1 | 5 |

Per-passage ranks (P1 to P5): original 4, 4, 4, 4, 4; A 3, 2, 3, 3, 3; B 2, 3, 2, 1, 2; C 1, 1, 1, 2, 1.

Every version, including the original, got `partial` on the same question (P5 q4), for partly different reasons: the scorer cited the missing "one past review" qualifier for all four, and for arm C also the change from "sometimes" to "some".

## What the checker found

- A: no differences.
- B, P5: "Codex is a reviewer, not an oracle" became "Codex is a reviewer and its findings can be wrong" (`can` added, `not` removed). The meaning holds.
- C, every passage. Some differences are meaning changes the readback questions did not probe: "sometimes over-corrected" became "some of the suggested wording over-corrected" (frequency became quantity); "never for multi-GPU" became "do not use it for multi-GPU"; channels were split out of "another person"; "only ships kernels to sm_90" became "only up to sm_90". Others are harmless, such as "how many files matched".

Before this run, the checker also flagged every `send/draft` rewritten as `send or draft` and every `~85 s` rewritten as `about 85 s`. Those false alarms were fixed after this run (commit "Stop flagging slash lists and approximation spellings"); `outputs/checker_results_before_fix.json` keeps the earlier output.

## Reading

On these five passages all three approaches kept the answers to the pre-written questions. The skill made the smallest edits and the checker found nothing to report, but the blind reader ranked its rewrites the hardest of the three to act on in four of five passages. The plain request produced the easiest text and also the only meaning shifts the checker found.

## Limits

- Five passages, one run per arm, one reader model, one scorer. No variance estimate.
- The questions hit a ceiling: even the original scored 22 of 23. They could not detect the shifts the checker found in arm C.
- The three-level grading scale is coarse. On P5 q4 the scorer noted that arm C replaced "sometimes" with "some", yet graded it `partial`, the same grade the original got for an unrelated omission.
- The generators and the reader are both Claude models.
- The passages are the owner's own text, already written with these rules in mind.

## Possible next steps

- Write harder questions aimed at scope, frequency, and actor, then rerun.
- Test a less conservative skill mode that names actors and expands fragments, with `ste-preserve.py` as the guard.
- Repeat each arm three times to see run-to-run variation.
