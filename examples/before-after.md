# Before / after: clarity without new meaning

These are illustrative editorial examples, not model evaluation results or certified STE text. The notes explain what a rewrite must preserve, including cases where clarification is impossible without more evidence.

## Direct action, known actor

**Before:** The agent will perform an analysis of the log and will then provide a report of the errors.

**After:** The agent will analyze the log. It will then report the errors.

The actor, future action, and order are unchanged. No new check or guarantee is added.

## A — Ambiguous fallback in a tool description

**Before:** This tool will attempt to synchronize state across the various backends that have been configured, and if a conflict is detected it may resolve it automatically depending on the strategy that has been set, or otherwise it will surface the conflict for manual review.

**After:** The tool tries to synchronize state across the configured backends. If a conflict is detected, it may resolve it automatically depending on the strategy that has been set, or otherwise it will surface the conflict for manual review.

**Needs clarification:** Does "otherwise" mean that automatic resolution is disallowed, or that the conflict remains unresolved for any reason?

The ambiguous clause stays. The rewrite neither invents a "read the strategy" operation nor chooses which outcomes require manual review. A longer sentence is preferable to an invented contract.

## B — An error is possible, not confirmed

**Before:** An error may have occurred while processing your request due to a possible mismatch in the expected data format, which could be caused by an outdated client version.

**After:** An error may have occurred while processing your request. The cause may be a mismatch in the expected data format. This mismatch could be caused by an outdated client version.

A processing error is not necessarily a failed request. The client is a possible cause, not a proven or frequent cause. There is no new server detail and no added instruction to check the client version.

## C — A recommendation remains a recommendation

**Before:** Once the upstream job has completed and assuming no errors were raised, the downstream agent should proceed to consume the output artifact, though it is worth noting that partial artifacts are sometimes produced under timeout conditions.

**After:** If the upstream job has completed and no errors were raised, the downstream agent should consume the output artifact. Partial artifacts are sometimes produced under timeout conditions.

Both prerequisites and `should` remain. The warning keeps `sometimes` and the timeout condition without inventing a causal mechanism. No instruction to wait, reject an artifact, or verify completeness is added. Those may be useful behavioral proposals, but they are not rewrites of the source.

## D — Integration claims are not data-residency guarantees

**Before:** Our caching layer is designed to slot seamlessly into your existing stack with minimal friction and no vendor lock-in; it leverages semantic similarity to dramatically reduce the cache misses that traditionally plague LLM workloads.

**After:** Our caching layer is designed to integrate seamlessly into your existing stack with minimal friction and no vendor lock-in. It uses semantic similarity to dramatically reduce the cache misses that traditionally affect LLM workloads.

This is a constrained illustration of editing an existing claim, not a reason to apply the skill to marketing copy. The claims about integration and performance remain unverified. "No vendor lock-in" does not establish where data is stored. The rewrite must not add a claim about local storage, exact-match caching, or measured performance. Removing unsupported promises is a separate content-review task.

## Different actions keep different names

**Before and after, unchanged:** Validate the JSON schema. Verify the signature. Confirm deployment with the operator. Remove the disk from the server. Delete the temporary file.

Different verbs here express different actions. A document-wide synonym list cannot establish equivalence. Use a consistent term only when it denotes the same concept.

## No-op is a valid result

**Before and after, unchanged:** Retry at most 3 times, and only for HTTP 503. Do not retry HTTP 429.

Shorter wording is not needed. The limit, condition, and prohibition are already explicit.
