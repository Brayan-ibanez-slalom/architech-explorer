# Governance & Security — Design Recommendations

> **Purpose:** ensure every architecture analysis addresses governance and security as
> **design concerns**, not as an afterthought bolted on after the pipeline works.
>
> **Grounding in TF1:** the course treats Security as a quality attribute driven by
> "boundary controls, policy enforcement, audit logs", and lists *security boundaries*
> and *data isolation* among the capabilities that are **expensive to introduce later**
> (slide 19). Governance decisions are therefore usually **near-irreversible** —
> retrofitting access control across dozens of live sources and consumers is costly.

## Core Principle
> Governance and security are **architectural capabilities**, not features.
> If they are not designed upfront, every new source, attribute, and consumer
> re-opens the same risk — and the cost of fixing it grows with adoption.

---

## 1. Governance Recommendations (include in every design where data is shared)

### 1.1 Data Ownership & Stewardship
- Assign a **data owner** (accountable for the domain) and **data steward** (operational quality) per source/domain.
- Document ownership in the catalog — unowned data becomes untrusted data.
- Relevant when a scenario mentions multiple source systems or cross-team consumption.

### 1.2 Data Catalog & Discoverability
- Register every dataset with business definitions, owner, freshness, and sensitivity classification.
- Without a catalog, "trusted view of the customer" objectives fail at the *adoption* stage even if the pipeline is correct.
- Options: OpenMetadata, DataHub (OSS); Collibra, Alation, Atlan (commercial); Unity Catalog, Snowflake Horizon, Purview, Dataplex (platform-native). See `technology-reference.md` §7.

### 1.3 Lineage & Traceability
- Capture **column-level lineage** from source → transformation → consumption.
- Required to answer "where did this number come from?" — directly supports the course's *traceability* principle.
- Prefer open standards (**OpenLineage**) to preserve optionality across engines.

### 1.4 Data Contracts & Schema Governance
- Define explicit **data contracts** between producers and consumers (schema, semantics, SLAs, breaking-change policy).
- Enforce **backward/forward compatibility** via a schema registry so producers can evolve independently (critical when firmware or source systems change on their own cadence).
- Version schemas; never silently mutate a contract that consumers depend on.

### 1.5 Data Quality Management
- Express quality as **measurable expectations** (completeness, uniqueness, referential integrity, freshness), consistent with the course rule that quality attributes must be measurable.
- Decide explicitly: does a failed check **block** the pipeline (quarantine) or **alert** only? This is an architectural trade-off between trust and availability.
- Implement a **quarantine/dead-letter path** for rejected records — never silently drop data.

### 1.6 Master Data & Reference Data Management
- Define survivorship rules (which source wins per attribute) and make them **explainable and auditable**.
- Preserve the ability to **reprocess history** when matching rules change — if you cannot, the matching logic becomes permanently frozen.

### 1.7 Lifecycle, Retention & Records Management
- Define retention per data class, plus archival tiers and defensible deletion.
- Address **right-to-erasure** feasibility *before* choosing an immutable storage/table format — append-only designs make deletion expensive.

### 1.8 Cost Governance (FinOps)
- Tag resources by domain/team; make cost per pipeline/consumer observable.
- Set budget alerts and detect runaway compute — relevant whenever a constraint says costs must "remain observable as usage grows".

---

## 2. Security Recommendations (include in every design handling sensitive data)

### 2.1 Data Classification
- Classify data (e.g., Public / Internal / Confidential / Restricted-PII) **at ingestion**, and propagate the classification as metadata through every layer.
- Policies should attach to **classification tags**, not to individual table names — this is what allows security to scale as new sources are added.

### 2.2 Access Control Model
- Prefer **ABAC (attribute/tag-based)** over per-table RBAC grants when sources grow continuously — RBAC grant sprawl is a common failure mode.
- Enforce **least privilege** and **purpose-based access** (access justified by use case, not by job title alone).
- Centralize policy definition; avoid re-implementing access rules per source or per consumer.

### 2.3 PII Protection Techniques
| Technique | Use when |
|---|---|
| **Masking / redaction** (dynamic) | Consumers need the row but not the sensitive value |
| **Tokenization** | Referential integrity across systems is needed without exposing raw values |
| **Hashing (salted)** | Join keys must work without reversibility |
| **Encryption at rest/in transit** | Baseline for all sensitive data (non-negotiable) |
| **Differential privacy / aggregation thresholds** | Analytics/ML on sensitive cohorts |
| **Pseudonymization** | GDPR-aligned reduction of identifiability while retaining analytical value |

### 2.4 Encryption & Key Management
- Encrypt in transit (TLS) and at rest by default.
- Decide explicitly on **customer-managed keys (CMK/BYOK)** vs. provider-managed — a regulatory constraint, not a preference.
- Never embed secrets in code or pipeline configs; use a secrets manager (Vault, Key Vault, Secrets Manager, Cloud KMS).

### 2.5 Auditability
- Log **who accessed what, when, and for what purpose** — and retain those logs per the compliance regime.
- Audit logs must be **tamper-evident** and stored separately from the data plane.
- If a requirement says "auditable", it is almost always an **ASR** — it shapes the access architecture itself.

### 2.6 Network & Boundary Controls
- Use private connectivity (private endpoints/VPC peering) for data plane traffic where regulation or sensitivity demands it.
- Define clear **trust boundaries** between ingestion, processing, and serving zones — the course explicitly calls out *security boundaries* as expensive to add later.
- Isolate non-production environments; never use raw production PII in development without masking.

### 2.7 Compliance & Residency
- Identify the applicable regime early (**GDPR, CCPA/CPRA, HIPAA, PCI-DSS, SOX, LGPD**, sector-specific rules).
- Check **data residency / sovereignty** constraints before choosing regions — this can invalidate an otherwise sound architecture.
- Map requirements to concrete capabilities: consent tracking, subject access requests, erasure, cross-border transfer controls.

### 2.8 AI/ML-Specific Considerations
- Control what sensitive data enters **feature stores, training sets, and model prompts** — models can memorize and leak PII.
- Track dataset lineage for models so training data can be audited and reproduced.
- Apply the same classification/masking policies to ML consumption paths as to BI paths.

---

## 3. How to Include This in a Scenario Analysis
When producing a report:
1. If the scenario mentions PII, regulation, auditability, or multi-team access →
   treat governance/security as a **candidate ASR**, and justify whether it is one.
2. Add a **"Governance & Security Recommendations"** section to the report covering, at minimum:
   classification, access-control model, PII protection technique, auditability, and lineage.
3. Place governance decisions on the **Cost of Change** spectrum — centralized access
   control and classification schemes are typically *near-irreversible* once many
   sources depend on them.
4. If compliance regime, retention, or residency is **not stated**, put it in
   **Open Questions** — do not assume GDPR (or any regime) applies.

## 4. Common Anti-Patterns to Flag
- Per-source, hand-rolled access rules (guarantees drift and audit gaps).
- Security added after the pipeline is built ("we'll lock it down later").
- Raw PII copied into dev/test environments.
- Masking applied only at the dashboard layer, leaving the underlying store exposed.
- No quarantine path — invalid or unclassified data silently dropped or silently admitted.
- Catalog/lineage treated as documentation rather than as an enforced control.
