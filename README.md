# Data Quality & Cleaning Platform

> **"Can I trust this dataset before I analyze it?"**

A data-quality and cleaning platform that profiles tabular datasets, detects quality problems across key dimensions (completeness, validity, consistency, uniqueness), executes controlled deterministic cleaning pipelines, preserves dataset lineage and version history, and exposes quality governance insights via a web application and Power BI.

---

## Architecture & Priority Hierarchy

```text
        ⭐⭐⭐⭐⭐
   DATA QUALITY ENGINE (Python / Pandas / PyArrow)
          │
     ┌────┴────┐
     ↓         ↓
  Cleaning   Profiling
     │         │
     └────┬────┘
          ↓
    Quality Score
          ↓
   Power BI Analytics (DAX / Governance)
          ↓
   Django REST Framework & React (Minimal UI)
```

- **Core Engine (Phases 1–5):** Data profiling, validation, rule-based transformation, and calibrated data quality scoring.
- **Hybrid Storage (Phase 6):** PostgreSQL for relational metadata, version pointers, and audit logs; local/object storage using Apache Parquet for dataset version snapshots.
- **API & UI (Phases 7–8):** Lightweight Django REST API and React single-page interface with user dataset ownership.
- **Governance BI (Phase 9):** Power BI dashboards visualizing platform-level data quality health, trends, and cleaning impacts.

---

## Directory Layout

```text
.
├── data/
│   ├── raw/             # Original raw files for testing (git-ignored)
│   └── sample/          # Small reference messy datasets
├── docs/                # Architecture specifications & Phase deliverables
├── src/                 # Reusable data profiling & cleaning engine
├── tests/               # Unit, integration, and edge-case tests
├── .gitignore
├── data_quality_cleaning_platform_project_planner.md
├── README.md
└── requirements.txt
```

---

## Getting Started

### 1. Set Up Virtual Environment

```bash
python -m venv .venv
# Windows PowerShell:
.venv\Scripts\Activate.ps1
# Windows Command Prompt:
.venv\Scripts\activate.bat
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Run Tests

```bash
pytest
```
