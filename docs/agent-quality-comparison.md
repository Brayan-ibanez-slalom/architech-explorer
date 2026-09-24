# Agent Quality Comparison — Before vs. After Instruction Refinement

> ⚠️ **Status: reasoned argument, NOT an executed A/B test.**
> This document was written by the same author as the instructions it evaluates,
> and predicts how the agent *would* respond. It has not been validated by running
> both instruction sets against a live agent and comparing real outputs.
> Treat it as a design rationale, not as evidence.
>
> An independent review later confirmed the risk of this closed loop: reports that
> self-certified as containing no invented requirements were found to contain several.
> Real verification now runs through `.github/workflows/agent-quality-review.yml`,
> which requires an **independent** agent verdict before a report PR can merge.

This document argues that refining `.github/copilot-instructions.md` (adding the
**Definition of Done** checklist and the **Handling Incomplete Input** rule) should
improve the quality of the agent's output. It compares how the agent would be expected
to respond to the *same intentionally incomplete* scenario submission, under the
original instructions vs. the refined ones.

## Test Input (deliberately incomplete — mirrors a real user submitting a rushed issue)

> "We're a logistics company. We want a real-time package tracking system so customers
> can see where their package is. We have a few warehouses and a mobile app."

Note what's missing: no numbers (throughput, latency, SLA), no constraints (budget,
timeline, team skills), no security/compliance notes, no growth projections.

---

## BEFORE (original instructions — no Definition of Done, no explicit "ask first" rule)

With only the general workflow description ("check completeness, ask questions if
missing"), a model under time/completion pressure tends to **fill gaps with
plausible-sounding assumptions** rather than stopping. A realistic "before" output:

> **Objectives:** O1: Provide real-time visibility into package location. O2: Improve
> customer satisfaction.
> **Quality attributes:** Latency < 2s, 99.9% availability *(invented — not provided)*.
> **ASRs:** Scale to 1M packages/day *(invented — not provided)*.
> **Decisions:** Use Kafka + GPS tracking + mobile push notifications.

**Problems:** Every number is fabricated. The "trade-offs" are generic and not tied to
any real constraint. This violates the course's own rule: *"Do not invent
requirements."* The output looks polished but is not trustworthy — a stakeholder
reading it might assume 1M packages/day and 99.9% availability were their own
requirements.

---

## AFTER (refined instructions — Definition of Done + mandatory clarifying-question rule)

Because the **Definition of Done** requires every quality requirement to have a
number sourced from the user or knowledge base, and the **Handling Incomplete Input**
rule blocks proceeding when that's not possible, the agent instead responds:

> Before I can produce ASRs and quality-attribute scenarios, I need a few specifics
> (referencing the blocked reasoning-chain steps):
> 1. **(Requirements)** What update latency is acceptable for customers seeing package
>    location — seconds, minutes?
> 2. **(ASRs — scale)** Roughly how many packages/day or concurrent tracking sessions
>    should this support today, and expected growth?
> 3. **(Constraints)** Is there a target launch date or budget ceiling?
> 4. **(Constraints — skills)** What's the team's experience with real-time/streaming
>    systems vs. batch?
> 5. **(Security)** Does package/customer location data have any privacy requirements?
>
> Once I have these, I'll produce the full objectives → constraints → requirements →
> ASRs → utility tree → decisions & trade-offs → cost of change → open-questions report.

**Result:** No fabricated numbers. Every subsequent artifact, once produced, will be
traceable to something the stakeholder actually said — matching the course's core
principle that architecture decisions must be *justified*, not guessed.

---

## Verdict: Value Gained

| Dimension | Before | After |
|---|---|---|
| Fabricated data in output | Yes (latency, scale, availability all invented) | None — blocked until provided |
| Traceability to source (per reasoning chain) | Broken — objectives don't justify invented numbers | Preserved — nothing proceeds without traceable input |
| Alignment with course rule "do not invent requirements" | Violated | Enforced |
| Stakeholder trust risk | High (looks authoritative but is fiction) | Low (agent is transparent about gaps) |
| Consistency across scenarios (verified via structural check) | Not enforced | Enforced via `validate-report.yml` + Definition of Done checklist |

**Conclusion:** the refined instructions produce a measurable quality gain — they
convert a plausible-but-fabricated answer into an honest, gap-driven clarification
step, which is the single most important behavior for a decision-justification tool
like this one.
