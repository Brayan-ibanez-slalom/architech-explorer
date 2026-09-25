# Architech Explorer

A knowledge base + agent workspace built from the **TF1 — Technical Foundations**
module of the Data Architect Academy (Slalom), designed so a **GitHub Copilot coding
agent** can pick up new architecture scenarios, ask clarifying questions, and produce
a full, structured architecture analysis grounded in the course methodology.

## Why this repo exists
Architecture reasoning should be traceable: business objectives → constraints →
requirements → Architecturally Significant Requirements (ASRs) → decisions →
trade-offs. This repo packages that methodology as machine-readable knowledge so an
agent can apply it consistently to new scenarios, instead of guessing at frameworks.

## Structure
```
.
├── knowledge-base/
│   ├── tf1-course-notes.md                                   # Structured extraction of the course (agent's source of truth)
│   ├── technology-reference.md                                # Vendor-neutral tool options by capability (guards against single-cloud bias)
│   ├── governance-and-security.md                             # Governance & security design recommendations
│   ├── instructor-notes.md                                     # Supplementary instructor notes
│   ├── scenario-facts.yml                                      # Fact manifest: every number/threshold a report cites must have an
│   │                                                            #   entry here (F## fact, U## unknown, or X## teaching example),
│   │                                                            #   each with a verbatim quote — replaces self-attested "(given)" labels
│   ├── provenance.lock                                         # sha256 pins for GitHub-issue-sourced scenarios; re-checked live by
│   │                                                            #   scripts/verify_provenance.py so a captured source can't drift or be forged
│   ├── sources/                                                 # Verbatim captures of each scenario's source (GitHub issue or case brief)
│   │   ├── verdant-grocers.source.txt
│   │   ├── solstice-health.source.txt
│   │   ├── northbridge-logistics.source.txt
│   │   └── space-airline-booking.source.txt
│   └── TF1_architectural-foundations-quality-attributes_instructor_slalom.pdf   # Original slide deck
├── docs/
│   ├── index.html                                             # Report gallery
│   ├── Customer360_Capstone_Solution.html                     # v1 reference example
│   ├── Customer360_Capstone_Solution_v2.html                  # v2 — vendor-neutral + governance (current quality bar)
│   ├── RetailIoT_Solution.html                                # Scenario A worked example
│   ├── VerdantGrocers_Solution.html                           # Scenario — inventory freshness without inventing a numeric SLA
│   ├── solstice-health_Solution.html                          # Scenario — HIPAA/PHI referral routing, single-cloud justified by a stated BAA
│   ├── northbridge-logistics_Solution.html                    # Scenario — fleet telemetry with several deliberately unresolved inputs
│   ├── space-airline-booking_Solution.html                    # Event case — airline booking platform, rate-limited legacy reservation system
│   ├── space-airline-booking_EventBrief.md                    # Same scenario, answering a live event's own literal deliverable format
│   └── agent-quality-comparison.md                            # Before/after instruction-refinement test
├── scripts/                                                    # Automated quality gates (all must pass before a report can be proposed)
│   ├── preflight.sh                                             # Single entry point — runs every check below, plus the regression suite
│   ├── check_citations.py                                       # Every number in a report must trace to a fact manifest ID
│   ├── check_decisions.py                                       # Every decision must have all 7 reviewable fields, substantive and non-negated
│   ├── check_workflows.py                                       # GitHub Actions workflow files parse and have valid triggers
│   ├── verify_manifest.py                                       # scenario-facts.yml quotes actually match their scoped source file(s)
│   ├── verify_provenance.py                                      # Re-fetches GitHub-issue-sourced scenarios live and compares pinned hashes
│   ├── test_gate.py                                              # Adversarial regression suite for the gates themselves (27 cases)
│   └── visible_text.py                                           # Shared HTML-to-visible-text helper used by the checkers
├── .github/
│   ├── copilot-instructions.md                                # Agent workflow rules (how to analyze a new scenario)
│   ├── ISSUE_TEMPLATE/new-scenario.md                          # Template to submit a new scenario for analysis
│   ├── CODEOWNERS
│   └── workflows/                                              # Setup steps, issue labelling, report structure validation
└── README.md
```

## Design principles enforced by the agent
These rules live in `.github/copilot-instructions.md` and are what make the output
trustworthy rather than merely well-formatted:

- **Never invent requirements.** Missing numbers, SLAs, or compliance regimes become
  *clarifying questions* or *open questions* — never assumptions.
- **Vendor neutrality.** Every technology recommendation names the required *capability*
  first, then offers options across **2–3 ecosystems** (open-source/portable,
  platform/lakehouse, hyperscaler), chosen by trade-off rather than familiarity. A bias
  audit of this repo found AWS-heavy recommendations; `knowledge-base/technology-reference.md`
  and an explicit anti-bias checklist exist to prevent recurrence. A single vendor is only
  acceptable when a stated constraint justifies it (see Solstice Health below).
- **Governance and security are design concerns.** Every report includes a
  Governance & Security section (classification, ABAC access model, PII protection,
  auditability, lineage, data contracts, quality/quarantine) because the course treats
  security boundaries as expensive to introduce later.
- **Traceability.** Nothing skips the chain: Objectives → Constraints → Requirements →
  ASRs → Decisions → Trade-offs → Cost of Change.

## Fact manifest, citations, and provenance (automated, not self-attested)
Every number, threshold, or absolute claim in a report must trace to an entry in
`knowledge-base/scenario-facts.yml`, cited inline as a fact ID (e.g. `[SOLH-F04]`).
This exists because earlier versions of this repo let a report append `(given)` to
an invented requirement and pass, since the marker was checked by the same untrusted
document that made the claim. Now:

- **`scripts/check_citations.py`** fails a report if a numeric claim has no matching
  manifest entry.
- **`scripts/verify_manifest.py`** confirms every manifest quote actually appears in
  its declared, scoped source file — one scenario's source can't vouch for another's.
- **`scripts/verify_provenance.py`** re-fetches the live GitHub issue for any
  GitHub-sourced scenario and compares its hash against `knowledge-base/provenance.lock`,
  so a captured source can't drift from or be forged against upstream.
- **`scripts/check_decisions.py`** fails a decision block unless all 7 reviewable
  fields (chosen approach, rejected alternative, why it's viable, sacrifice, gain,
  reversal condition, unresolved fact) are present and substantive.
- **`scripts/preflight.sh`** is the single entry point that runs all of the above
  plus an adversarial regression suite (`scripts/test_gate.py`) against the gates
  themselves, and must pass before any PR is opened.
- An **independent review verdict** (a second, separate reviewer — never the report's
  own author grading itself) is required after preflight passes and before a PR opens.
  Passing gates proves fields are *present and sourced* — it does not prove the
  reasoning is *correct or wise*; that judgment is exactly what the independent
  review step exists to make.

## How to use this repo with GitHub Copilot

1. **Open a new issue** using the *"New Architecture Scenario"* template and fill in
   whatever business context, objectives, requirements, and numbers you already know.
   Leave anything unknown blank — don't guess.
2. **Assign the issue to Copilot** (or start a Copilot coding agent session referencing
   the issue). The agent will:
   - Check your input against `knowledge-base/tf1-course-notes.md`.
   - Ask follow-up questions if objectives, constraints, or measurable quality
     attributes are missing or ambiguous — see Aperture Media below for what a
     correctly-blocked scenario looks like.
   - Once sufficient, produce the full reasoning chain: objectives → constraints →
     functional/quality requirements → quality-attribute scenarios → ASRs → utility
     tree → architecture decisions & trade-offs → recommended tools → open questions
     for the stakeholder.
   - Add the scenario's facts to `knowledge-base/scenario-facts.yml` with verbatim
     quotes *before* writing the report, then deliver the result as a new HTML report
     under `docs/`, citing a fact ID next to every number, following the same visual
     style (Mermaid diagrams, tables, cost-of-change spectrum) as
     `docs/Customer360_Capstone_Solution_v2.html`.
   - Run `./scripts/preflight.sh` and obtain an independent review verdict before
     proposing a PR.
3. Review the generated report, iterate via PR comments if trade-offs need revisiting.

## Worked Scenarios
Beyond the two capstone reference examples, the following scenarios have been run
through the full agent workflow end-to-end (facts manifest → report → automated
gates → independent review):

| Scenario | Source | What it tests |
|---|---|---|
| **Retail IoT Monitoring** | Course scenario | Streaming ingestion at scale, sub-200ms latency, AZ failover |
| **Verdant Grocers** | GitHub issue | A deliberately imprecise freshness target ("within a few minutes") that must *not* be converted into an invented numeric SLA |
| **Solstice Health** | GitHub issue | A fully-specified HIPAA/PHI scenario where narrowing to a single cloud (Azure) is genuinely justified by a stated BAA + data-residency constraint, not familiarity |
| **Northbridge Logistics** | GitHub issue | A mixed scenario: solid core facts alongside 5 explicitly-undetermined items (compliance regime, growth rate, budget, role definitions, cloud vendor) that must be kept out of the facts manifest and routed to Open Questions instead of guessed |
| **SPACE — Airline Booking Platform** | Local case brief (not a GitHub issue) | A technically demanding live-event brief with a capacity-constrained legacy reservation system, asynchronous payment confirmation, and a "no maintenance window, ever" constraint — also produced a second, presentation-ready deliverable (`space-airline-booking_EventBrief.md`) answering the brief's own literal requested format |
| **Aperture Media** *(not committed — no report exists)* | GitHub issue | A deliberately vague scenario (no numbers, no named constraints) used to confirm the agent asks clarifying questions instead of fabricating a report |

## Reference Example
`docs/Customer360_Capstone_Solution_v2.html` is a complete worked example (Customer 360
platform capstone) showing the expected output format and depth — open it in a browser
to see the target quality bar for any new scenario.

## Course Source
Slide deck: `knowledge-base/TF1_architectural-foundations-quality-attributes_instructor_slalom.pdf`
— Data Architect Academy, Slalom. Instructor: Iván Trebilcock.
