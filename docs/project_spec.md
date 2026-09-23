# Project Specification — Phase 0

## V0.1 — Problem & Target Audience

- **Problem:** Data analysts and business intelligence teams frequently spend 60–80% of their time fixing dirty data or, worse, producing misleading reports from untrusted datasets containing duplicates, invalid formats, mixed types, and hidden nulls.
- **Goal:** Provide an automated, deterministic system that answers: *"Can I trust this dataset before I analyze it?"*
- **Target User:** Data Analysts, Analytics Engineers, and Business Users handling CSV/Excel files who need immediate profiling, transparent cleaning, and auditable version tracking.
- **Clean Data Definition:** A dataset that satisfies core data quality dimensions:
  1. *Completeness* (no unexpected nulls or missing values)
  2. *Validity* (values adhere to domain constraints, regex patterns, and data types)
  3. *Consistency* (standardized casing, uniform categories, normalized date formats)
  4. *Uniqueness* (no duplicate records or duplicate primary keys)

---

## V0.2 — MVP Boundaries

### In-Scope (MVP)
- Tabular file uploads: CSV and Excel (.xlsx) capped at ≤ 25 MB.
- In-memory synchronous processing for MVP (fast feedback loop).
- Automated dataset profiling (row/col count, types, null counts, duplicate counts, descriptive statistics).
- Issue detection engine (identifies missing values, duplicates, format anomalies, out-of-bounds numbers, and outliers).
- 13-step deterministic data cleaning pipeline.
- Quality score generation (dimensional breakdown + overall score).
- Hybrid storage model (PostgreSQL for metadata & history; local Parquet for internal dataset snapshots).
- Cleaned dataset export to CSV (with formula-injection prevention).
- Basic user dataset ownership & API isolation (IDOR protection).
- Minimal Django REST API & minimal React single-page UI.
- Power BI Governance dashboard for platform-level quality metrics.

### Deferred (Post-MVP)
- Celery / Redis asynchronous worker queues (to be introduced when scaling beyond 25 MB).
- Real-time streaming & automated scheduled ingestion.
- Complex multi-tenant enterprise org hierarchies and team approvals.
- Advanced machine learning auto-remediation.

---

## V0.3 — End-to-End Workflow

```text
1. Upload Dataset (CSV/XLSX ≤ 25MB)
         ↓
2. Profile & Detect Issues (Structural & statistical profiling)
         ↓
3. Review Quality Report (View quality score & dimension breakdown)
         ↓
4. Select Cleaning Actions (User picks operations & parameters)
         ↓
5. Execute Deterministic Cleaning Pipeline (13-step ordered transformation)
         ↓
6. Generate Cleaned Version & Audit Log (Preserve raw file, save Parquet version)
         ↓
7. Compare Before & After (Inspect delta in row counts, quality scores, and resolved issues)
         ↓
8. Export Cleaned Dataset (Download safe CSV)
         ↓
9. Platform Quality Governance in Power BI (Analyze aggregated health metrics)
```
