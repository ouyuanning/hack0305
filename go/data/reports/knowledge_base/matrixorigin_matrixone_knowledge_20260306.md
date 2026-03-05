# MatrixOne Issue Knowledge Base

This knowledge base summarizes recurring patterns, module ownership, labeling conventions, and critical issue categories observed across the MatrixOne GitHub issue corpus (as of snapshot `2026-03-05`). It is intended for engineers, QA, PMs, and support teams to accelerate triage, assignment, and root-cause analysis.

---

## 🔧 Core Modules & Ownership

| Module / Area              | Key Responsibilities                                                                 | Primary Owners (from assignees & labels) | Notes |
|----------------------------|--------------------------------------------------------------------------------------|------------------------------------------|-------|
| **Window Functions**       | `first_value`, `last_value`, `lead`, `lag`, `ntile`, `percent_rank`, frame clauses, ordering, partitioning | `Ariznawlll`, `heni02`                  | High MySQL compatibility gap; many `kind/compatibility` + `windowfunction` issues. Critical for analytics workloads. |
| **Vector Indexing (ANN)**   | HNSW, IVF-FLAT index creation, search, concurrency safety, memory management, rollback, panic recovery | `heni02`, `Ariznawlll`, `iamlinjunhong` | Top source of `severity/s0` panics (`makeslice: cap out of range`, `top`/`shuffle` crashes), OOMs, and DDL rollback failures. |
| **SQL Parser & Execution** | `WITH ... INSERT`, `SELECT * FROM result_scan(...)`, hint parsing, syntax error messages, `ORDER BY ... LIMIT` top-k logic | `heni02`, `Ariznawlll`, `gouhongshen`    | Poor error messaging (e.g., generic `syntax error at line X column Y`) is a frequent UX complaint. `result_scan` failures indicate query result lifecycle bugs. |
| **Compatibility Layer**    | MySQL protocol fidelity: `LIKE` semantics, `currval()` behavior, `save_query_result` with hints, client-specific quirks (Tableau, Superset, Kettle, low-version MySQL clients), `YEAR` type support | `Ariznawlll`, `heni02`                   | Dominated by `area/compatibility`, `kind/compatibility`, `severity/s0`. Drives adoption — fixes have high impact. |
| **Data Loading & Ingestion** | `LOAD DATA` (CSV, Parquet, compressed formats), column mapping, type coercion, schema inference, performance bottlenecks | `robll-v1`, `heni02`, `Ariznawlll`       | `flate`/`gzip` load is 6–7× slower than uncompressed. Parquet column name mismatches (`column not found`) are common. |
| **Temporary Tables & Session State** | `CREATE TEMPORARY TABLE`, auto-increment behavior in pessimistic mode, session isolation, `last_insert_id()` consistency | `Ariznawlll`, `heni02`                   | `attention/refactor-related` label indicates legacy design debt. Temp table cloning and `auto_increment` non-determinism are persistent issues. |
| **Full-Text Search (FTS)** | `MATCH() AGAINST()`, `FULLTEXT` index creation, parser (ngram), concurrency scaling, memory pressure | `Ariznawlll`                             | Severe concurrency ceiling (~50 QPS max); under-resourced vs. ES benchmark. Labeled `phase/testing`, `severity/s0`. |
| **Python UDF & SDK**       | Python function registration, execution sandbox, parameter binding, SDK connection string parsing (special chars `@`, `#`) | `Ariznawlll`, `heni02`                   | SDK fails on passwords with URL-reserved chars. UDF errors lack actionable diagnostics. |
| **Performance & Scalability** | Sysbench throughput regression, trace overhead (`trace.Start`), spill efficiency, group operator memory bloat, vector load speed | `heni02`, `gouhongshen`, `robll-v1`      | `area/performance` issues often involve subtle resource contention or algorithmic inefficiency (e.g., single-batch aggregation). |
| **Backup/Restore & Cloning** | `CLONE DATABASE`, `RESTORE CLUSTER`, snapshot consistency, duplicate key conflicts during restore, metadata synchronization | `gouhongshen`, `Ariznawlll`              | `restore` failures show race conditions between metadata and data restoration. `clone` can silently drop tables. |

---

## 🏷️ Label Taxonomy & Usage Guide

### Priority & Severity
| Label             | Meaning                                                                 | Prevalence | Notes |
|-------------------|-------------------------------------------------------------------------|------------|-------|
| `priority/p0`     | Highest business impact; blocks GA, major customer, or core functionality. | Very High  | Used for *all* `windowfunction`, `compat