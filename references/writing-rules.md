# STE background and this fork's boundaries

ASD-STE100 is a controlled-language standard for technical documentation. The official description of Issue 9 (January 2025) lists 53 writing rules in 9 sections, a dictionary of approximately 900 approved words, and allowances for domain-specific technical nouns and verbs. The dictionary is not included in this repository.

Source: [ASD-STE100 — About STE](https://www.asd-ste100.org/about_STE.html). Request the authoritative standard from the [official downloads page](https://www.asd-ste100.org/STE_downloads.html).

## Strict-mode targets inherited from the upstream summary

These are an abbreviated editorial reference, not a substitute for the standard or proof of compliance:

| Area | STE target |
|---|---|
| Terminology | Approved meanings and parts of speech, supplemented by domain terminology |
| Actions | Direct verbs; active voice in procedures; one instruction per sentence |
| Length | Up to 20 words for procedural sentences and 25 for descriptive sentences |
| Structure | Short noun clusters; explicit sentence parts; one topic per paragraph |
| Grammar | Simple verb forms; no semicolons; avoid phrasal verbs |
| Layout | Lists where they clarify sequences or conditions |

This fork narrows two targets. Strict mode keeps established technical compounds and software jargon when a plainer form would lose technical meaning. It does not apply sentence or structure limits to debugging hypotheses, design trade-offs, or decision records. See the Modes section of `SKILL.md`.

The [upstream reference](https://github.com/danyuchn/asd-ste100-skill/blob/7d4a135a199a5d7447c4886bcd7ffe742a627bc9/references/writing-rules.md) contains the longer paraphrased summary. Consult the official standard when exact rules matter.

## Adaptation, not a transfer of guarantees

This fork uses those ideas as clarity preferences. It does not assume that aviation-oriented restrictions improve LLM task success. Keeping a technical term, compound tense, semicolon, or longer sentence is appropriate when it preserves meaning or improves understanding.

Consistency means one name for the same concept, not one verb for several different operations. Preserve epistemic uncertainty, permission, obligation, temporal meaning, and logical scope. Never infer facts or requirements merely to make a sentence more explicit.

The optional linter offers surface-pattern hints. It does not use the official dictionary, compare a source with a rewrite, or establish semantic equivalence. Assess usefulness by what the recipient understands or does, not by the number of style findings.
