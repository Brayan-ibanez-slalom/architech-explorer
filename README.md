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
│   └── TF1_architectural-foundations-quality-attributes_instructor_slalom.pdf   # Original slide deck
├── docs/
│   └── Customer360_Capstone_Solution.html                    # Fully worked reference example (style + depth template)
├── .github/
│   ├── copilot-instructions.md                                # Agent workflow rules (how to analyze a new scenario)
│   ├── ISSUE_TEMPLATE/new-scenario.md                          # Template to submit a new scenario for analysis
│   └── workflows/copilot-setup-steps.yml                       # Cloud agent environment setup
└── README.md
```

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
