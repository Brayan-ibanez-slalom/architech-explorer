# Technology Reference — Vendor-Neutral Options by Capability

> **Purpose:** prevent single-vendor bias in architecture recommendations.
> **Rule:** always reason from the *capability the ASR demands*, then present options
> across **at least 2–3 ecosystems** (one hyperscaler, one platform/lakehouse vendor,
> one open-source/portable option) — and state the trade-off that would make you pick
> one over the others. Never recommend a tool because it is popular or familiar.

## How to use this file
1. Identify the capability the ASR requires (left column).
2. Pick candidate options from **multiple** ecosystem columns.
3. Justify the selection by the **trade-off** (cost, lock-in, team skills, latency, governance), not by brand.
4. If the client has an existing cloud/platform commitment, say so explicitly as a *constraint* — that is a legitimate reason to narrow options, and it must be stated, not assumed.

---

## 1. Streaming / Event Ingestion
| Ecosystem | Options |
|---|---|
| Open source / portable | Apache Kafka, Apache Pulsar, Redpanda, NATS JetStream |
| Managed OSS | Confluent Cloud, Aiven for Kafka, Redpanda Cloud |
| AWS | Amazon MSK, Amazon Kinesis Data Streams |
| Azure | Azure Event Hubs, Azure Service Bus |
| Google Cloud | Google Cloud Pub/Sub |
| Lakehouse-native | Databricks Structured Streaming (with Auto Loader), Snowflake Snowpipe Streaming |

**Trade-off axes:** operational burden (self-managed Kafka vs. managed), portability/lock-in, per-GB cost at 50K+ events/sec, ordering & exactly-once guarantees, team streaming maturity.

## 2. Batch / ELT Ingestion & Connectors
| Ecosystem | Options |
|---|---|
| Open source | Airbyte (OSS), Meltano, Singer taps, Apache NiFi |
| Commercial SaaS | Fivetran, Matillion, Stitch, Rivery |
| AWS | AWS Glue, AWS DMS |
| Azure | Azure Data Factory, Synapse Pipelines |
| Google Cloud | Cloud Data Fusion, Dataflow (batch mode) |
| Lakehouse-native | Databricks Lakeflow Connect, Snowflake native connectors / Openflow |

**Trade-off axes:** connector breadth vs. per-row cost, time-to-onboard a new source (directly relevant to a "2-week onboarding" SLA), custom-source extensibility, egress/compute cost model.

## 3. Transformation & Processing
| Ecosystem | Options |
|---|---|
| Open source | Apache Spark, Apache Flink (streaming), dbt-core, Apache Beam |
| Commercial | dbt Cloud, Databricks (Spark/Photon), Snowflake (Snowpark, dynamic tables) |
| AWS | EMR, Glue ETL, Managed Service for Apache Flink |
| Azure | Synapse Spark, Azure Databricks, Stream Analytics |
| Google Cloud | Dataproc, Dataflow (Beam) |

**Trade-off axes:** SQL-first (dbt/Snowflake) vs. code-first (Spark/Flink) — maps directly to team skills constraints; streaming-native (Flink) vs. micro-batch (Spark Structured Streaming); compute cost elasticity.

## 4. Storage / Lakehouse & Table Formats
| Ecosystem | Options |
|---|---|
| Open table formats | Apache Iceberg, Delta Lake, Apache Hudi |
| Object storage | Amazon S3, Azure Data Lake Storage Gen2, Google Cloud Storage, MinIO (self-hosted/portable) |
| Warehouse / lakehouse | Snowflake, Databricks (Unity Catalog + Delta), BigQuery, Amazon Redshift, Azure Synapse, ClickHouse, DuckDB (small-scale/embedded) |

**Trade-off axes:** open format (Iceberg/Delta → avoids lock-in, enables multi-engine reads) vs. proprietary storage; separation of storage & compute; cost predictability; time-travel/versioning support. **Note:** table format and partitioning strategy are *near-irreversible* decisions per the Cost of Change model — favor open formats when uncertainty is high (preserve optionality).

## 5. Orchestration
| Ecosystem | Options |
|---|---|
| Open source | Apache Airflow, Dagster, Prefect, Argo Workflows, Kestra |
| Managed | Astronomer, Google Cloud Composer, Amazon MWAA, Azure Data Factory, Dagster+ |
| Lakehouse-native | Databricks Workflows, Snowflake Tasks |

**Trade-off axes:** asset-aware lineage (Dagster) vs. task-centric maturity/ecosystem (Airflow); managed vs. self-hosted ops cost. Orchestration choice is typically **partially reversible** — pipelines can be ported, but at a migration cost.

## 6. Identity Resolution / MDM
| Ecosystem | Options |
|---|---|
| Open source | Zingg (ML-based entity resolution), Splink (probabilistic record linkage), RecordLinkage (Python) |
| Commercial / specialist | Senzing, Informatica MDM, Reltio, Tamr |
| Cloud-native | AWS Entity Resolution, Azure (custom via Synapse/Databricks), Google Cloud (custom) |
| Lakehouse-native | Databricks (Spark ML pipelines), Snowflake (Snowpark-based matching) |

**Trade-off axes:** deterministic vs. probabilistic/ML matching accuracy; explainability & auditability of merges (critical when PII is involved); build-vs-buy cost; ability to reprocess history when rules change.

## 7. Data Governance, Catalog & Lineage
| Ecosystem | Options |
|---|---|
| Open source | OpenMetadata, DataHub, Apache Atlas, Marquez (OpenLineage), Amundsen |
| Commercial | Collibra, Alation, Atlan, Informatica |
| Cloud-native | AWS Glue Data Catalog + Lake Formation, Microsoft Purview, Google Dataplex/Data Catalog |
| Lakehouse-native | Databricks Unity Catalog, Snowflake Horizon |

**Trade-off axes:** breadth of automated lineage capture vs. manual stewardship effort; open standards support (OpenLineage) vs. vendor-integrated depth; cost per data asset.

## 8. Access Control, Masking & Policy Enforcement
| Ecosystem | Options |
|---|---|
| Open source | Open Policy Agent (OPA), Apache Ranger, Cerbos |
| Commercial | Immuta, Privacera, Satori, BigID (discovery/classification) |
| Cloud-native | AWS Lake Formation (row/column-level), Azure Purview + RBAC, Google BigQuery column-level security & policy tags |
| Lakehouse-native | Databricks Unity Catalog (row filters, column masks, ABAC), Snowflake (dynamic data masking, row access policies, tag-based policies) |

**Trade-off axes:** centralized policy engine (portable, consistent across engines) vs. native enforcement (simpler, but per-platform re-implementation); attribute-based (ABAC) vs. role-based (RBAC) scalability as sources grow.

## 9. Data Quality & Observability
| Ecosystem | Options |
|---|---|
| Open source | Great Expectations, Soda Core, dbt tests, Deequ, Elementary |
| Commercial | Monte Carlo, Soda Cloud, Bigeye, Anomalo |
| Cloud/platform-native | Databricks Lakehouse Monitoring, Snowflake data metric functions, AWS Glue Data Quality |

**Trade-off axes:** declarative test coverage (cheap, explicit) vs. ML-based anomaly detection (broader, noisier); in-pipeline blocking vs. post-hoc alerting.

## 10. Secrets, Encryption & Key Management
| Ecosystem | Options |
|---|---|
| Open source | HashiCorp Vault, SOPS, External Secrets Operator |
| Cloud-native | AWS KMS + Secrets Manager, Azure Key Vault, Google Cloud KMS + Secret Manager |

**Trade-off axes:** BYOK/HYOK (customer-managed keys) for regulatory control vs. operational simplicity of provider-managed keys.

---

## Anti-Bias Checklist (apply before recommending any tool)
- [ ] **"¿Para qué?"** — can I state the outcome this tool serves, the business objective it traces to, and the ASR that makes it necessary? If not, it is a preference, not a decision.
- [ ] Did I state the **capability** required before naming any product?
- [ ] Did I offer options from **at least 2–3 different ecosystems** (not all one cloud)?
- [ ] Did I include at least one **open-source / portable** option where one genuinely exists?
- [ ] Did I justify the recommendation by a **trade-off tied to a stated constraint or ASR** — not by popularity, familiarity, or market share?
- [ ] If I narrowed to one vendor, did I explicitly state the **constraint** that justified it (e.g., "client is already standardized on Azure")?
- [ ] Did I flag **lock-in / reversibility** implications using the Cost of Change model?
