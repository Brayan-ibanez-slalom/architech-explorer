# TF1 — Technical Foundations: Architecture as Decision-Making

Source: `TF1_architectural-foundations-quality-attributes_instructor_slalom.pdf`
Data Architect Academy — Slalom. Instructor: Iván Trebilcock.

> This file is a structured, agent-readable extraction of the course slide deck.
> It is the **primary knowledge base** the agent must ground its answers in.

## Core Thesis
Architecture is **justified decision-making under constraint** — not the selection of fashionable tools.
The job is to make trade-offs that are traceable back to business objectives, not to pick a technology first.

## Learning Objectives
- **Understand:** Architecture is about decisions and trade-offs, not frameworks/diagrams. Functional requirements vs. quality attributes. Architecturally Significant Requirements (ASRs) and cost of change.
- **Apply:** Identify business objectives and constraints for a scenario. Write measurable quality-attribute scenarios. Build a Utility Tree; trace decisions to trade-offs.
- **Evaluate:** Assess whether a decision is justified by objectives and constraints. Identify hidden trade-offs in existing architectures. Facilitate a team through the objectives → decisions chain.

## What is Architecture?
- Architecture translates business objectives, constraints, and requirements into a coherent system.
- Architectural decisions are **long-term strategies**, not implementation details.
- Architecture describes what the system can do, how well, and how it can evolve.
- Even granular decisions (e.g., "the right table granularity") are architectural — they affect performance, cost, scalability, and future flexibility.
- Tools don't replace judgment: know what a tool solves, and what it doesn't.

## Inputs to Architectural Design
| Input | Description |
|---|---|
| Business objectives | Value the system must deliver: revenue, CX, data volume, real-time analytics |
| Constraints | Limits on the solution space: budget, timeline, regulation, infrastructure, expertise |
| Functional requirements | What the system must do: create orders, store data, generate reports, process payments |
| Quality attributes | How well the system performs: performance, scalability, availability, security, modifiability |

## Functional vs. Quality Requirements
- **Functional** — what the system does (e.g., create orders, store data, generate reports, process payments).
- **Quality** — how well it performs (e.g., response < 1s, 99.9% availability, scale 10x without re-architecture, PII policies enforced centrally).

## Quality Attributes as Architecture Drivers
| Quality Attribute | Typical Architectural Response |
|---|---|
| Performance | Caching, async processing, load balancing |
| Scalability | Distributed architecture, event streaming |
| Availability | Redundancy, failover, replication |
| Security | Boundary controls, policy enforcement, audit logs |
| Modifiability | Layering, decoupling, schema evolution |

## Quality-Attribute Scenario Structure
Use this 6-part structure to make a quality attribute **measurable** before choosing architecture:
1. **Source** — who or what triggers the event
2. **Stimulus** — the event or condition
3. **Environment** — the conditions under which the stimulus occurs
4. **Artifact** — part of the system affected
5. **Response** — how the system reacts
6. **Response Measure** — how success is measured

Example measure: p95 ingestion latency < 200ms with zero event loss.

## Architecturally Significant Requirements (ASRs)
An ASR is a requirement that **materially influences the structure, behavior, or major design decisions** of the system. Not every requirement is architecturally significant.

Common pressure categories:
- **Scale pressure** — e.g., support 10M concurrent users or 50K events/sec.
- **Recovery pressure** — e.g., recover in <30s or meet RTO/RPO commitments.
- **Compliance pressure** — strict data security, access control, masking, auditability.

## Utility Tree
A Utility Tree does **not** tell you what to build. It tells you **what you cannot afford to get wrong**.
Structure: Quality attribute → concrete scenario → priority rating (business importance, implementation difficulty/risk).

## Cost of Change
| Category | Examples |
|---|---|
| Reversible | Table naming, dashboard layout, report format |
| Partially reversible | Orchestration tool, cloud region |
| Near-irreversible | Storage architecture, schema design, coupling between layers |

The harder a decision is to reverse, the more intentional we should be about making it.

## Architecture Must Evolve
- **Design upfront for critical capabilities** — identify capabilities expensive to introduce later (scalability, security boundaries, recoverability, interoperability, data isolation).
- **Allow the design to evolve** — not every implementation detail needs to be decided upfront.
- **Preserve optionality** — when uncertainty is high, avoid unnecessary irreversible decisions.
- **Continuously reassess** — revisit architecture and assumptions as objectives/constraints/quality attributes change.

## The Reasoning Chain
Every significant decision should be traceable back to the business objective:

```
1. Business objectives → 2. Constraints → 3. Functional + Quality requirements → 4. ASRs → 5. Decisions + Trade-offs
```

- Skip a step and the decision loses its justification.
- Quality attributes become useful only when specific and measurable.
- ASRs narrow the design space and expose the trade-offs worth discussing.

## Worked Example: Scenario A — Retail IoT Monitoring Platform
**Business context:** A retail company operates 500 stores with IoT devices generating continuous telemetry. Operations teams want to monitor conditions, detect issues, and support near-real-time analytics. Device count is expected to grow as the platform expands to new regions.

**Functional requirements:**
- Receive telemetry events from devices across all stores
- Validate incoming events
- Persist accepted events for downstream processing
- Make data available to analytics and operational applications
- Support new versions of device event schemas over time

**Operating conditions (ASR-level):**
- 50K events/sec peak ingestion bursts during business hours
- p95 ingestion latency < 200ms during peak load
- Recovery from a single availability-zone failure in <30 sec
- Deploy a new event schema without pipeline downtime, <1 day

**Additional context:**
- Events may contain device/store/customer/loyalty identifiers requiring controlled access.
- Device firmware evolves independently and may introduce new event schema versions.
- The delivery team has strong batch-processing experience but limited streaming experience.

## Capstone Reference Case: Customer 360 (see `docs/Customer360_Capstone_Solution.html` for the fully worked solution)
**Business context:** A retail company wants a Customer 360 capability combining customer information and interactions across e-commerce, loyalty, support, and marketing systems, to support analytics, personalization, customer service, and future Data Science use cases.

**Current scale:** 20M customers · 5M interactions/day · 4 initial source systems · 3 years historical data · 3× interaction growth expected within 2 years.

**Operating conditions:**
- Daily dashboards ready by 7:00 AM
- Marketing data can tolerate several hours of latency
- Customer Service interactions available within 15 minutes
- Customer data contains PII requiring controlled, auditable access
- 2–4 new sources/year; a standard source should onboard within 2 weeks
- First production release required within 4 months
- Infrastructure/processing costs must remain observable as usage grows

**Task format required for any new capstone scenario:**
2–3 objectives → key constraints → functional and quality requirements → 2 quality-attribute scenarios → 3 ASRs → 3 architecture decisions → trade-offs. Do not invent requirements — identify gaps and state what to ask the stakeholder.

## Related Frameworks (Supplementary — Not from the Deck)
These are widely recognized industry frameworks that reinforce the same reasoning
chain taught in TF1. Use them for extra rigor or terminology, but never replace the
deck's methodology or its required output structure with these.

| Framework | Purpose | How it maps to TF1 |
|---|---|---|
| **ATAM** (Architecture Tradeoff Analysis Method, SEI/Carnegie Mellon) | Structured method to evaluate architecture against multiple competing quality attributes | Formalizes the Utility Tree + trade-off analysis taught in this course |
| **ADR** (Architecture Decision Records) | Lightweight, versioned document capturing one decision, its context, and consequences | Use to persist each "Decision + Trade-off" from the reasoning chain as a durable artifact (`decisions/NNNN-title.md`) |
| **C4 Model** (Context, Containers, Components, Code) | Layered diagramming notation for visualizing architecture at increasing detail | Complements (does not replace) the Mermaid architecture diagrams in `docs/*.html` |
| **Cloud Well-Architected Frameworks** (AWS/Azure/GCP) | Pillars: Operational Excellence, Security, Reliability, Performance Efficiency, Cost Optimization, Sustainability | Each pillar maps to one or more TF1 quality attributes (e.g., Reliability → Availability, Cost Optimization → Cost of Change) |

**When to cite these:** only to strengthen a decision's justification (e.g., "this
follows the AWS Well-Architected Reliability pillar") — never as a substitute for the
Objectives → Constraints → Requirements → ASRs → Decisions chain.

## Key Takeaways
Great architects do not start with solutions. They start by understanding the problem space:
- Understanding business objectives
- Respecting constraints
- Designing for quality attributes
- Making deliberate trade-offs
- Controlling long-term cost of change

> Architecture is justified decision-making under constraint.
