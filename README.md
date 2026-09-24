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
│   └── TF1_architectural-foundations-quality-attributes_instructor_slalom.pdf   # Original slide deck
├── docs/
│   ├── index.html                                             # Report gallery
│   ├── Customer360_Capstone_Solution.html                     # v1 reference example
│   ├── Customer360_Capstone_Solution_v2.html                  # v2 — vendor-neutral + governance (current quality bar)
│   ├── RetailIoT_Solution.html                                # Scenario A worked example
│   └── agent-quality-comparison.md                            # Before/after instruction-refinement test
├── .github/
│   ├── copilot-instructions.md                                # Agent workflow rules (how to analyze a new scenario)
│   ├── ISSUE_TEMPLATE/new-scenario.md                          # Template to submit a new scenario for analysis
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
  and an explicit anti-bias checklist exist to prevent recurrence.
- **Governance and security are design concerns.** Every report includes a
  Governance & Security section (classification, ABAC access model, PII protection,
  auditability, lineage, data contracts, quality/quarantine) because the course treats
  security boundaries as expensive to introduce later.
- **Traceability.** Nothing skips the chain: Objectives → Constraints → Requirements →
  ASRs → Decisions → Trade-offs → Cost of Change.

## How to use this repo with GitHub Copilot

1. **Open a new issue** using the *"New Architecture Scenario"* template and fill in
   whatever business context, objectives, requirements, and numbers you already know.
   Leave anything unknown blank — don't guess.
2. **Assign the issue to Copilot** (or start a Copilot coding agent session referencing
   the issue). The agent will:
   - Check your input against `knowledge-base/tf1-course-notes.md`.
   - Ask follow-up questions if objectives, constraints, or measurable quality
     attributes are missing or ambiguous.
   - Once sufficient, produce the full reasoning chain: objectives → constraints →
     functional/quality requirements → quality-attribute scenarios → ASRs → utility
     tree → architecture decisions & trade-offs → recommended tools → open questions
     for the stakeholder.
   - Deliver the result as a new HTML report under `docs/`, following the same visual
     style (Mermaid diagrams, tables, cost-of-change spectrum) as
     `docs/Customer360_Capstone_Solution.html`.
3. Review the generated report, iterate via PR comments if trade-offs need revisiting.

## Reference Example
`docs/Customer360_Capstone_Solution.html` is a complete worked example (Customer 360
platform capstone) showing the expected output format and depth — open it in a browser
to see the target quality bar for any new scenario.

## Course Source
Slide deck: `knowledge-base/TF1_architectural-foundations-quality-attributes_instructor_slalom.pdf`
— Data Architect Academy, Slalom. Instructor: Iván Trebilcock.
