-- =============================================================================
-- Data Quality & Cleaning Platform — PostgreSQL Relational Schema
-- Phase 6: V6.0 – V6.5
-- Hybrid Storage Architecture: Stores metadata, quality scores, issue logs,
-- and dataset version lineage. (Actual data tables live in Parquet storage).
-- =============================================================================

-- Enable UUID extension if using PostgreSQL
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 1. Datasets Table (Top-level logical container)
CREATE TABLE IF NOT EXISTS datasets (
    id VARCHAR(36) PRIMARY KEY,
    name VARCHAR(255) NOT NULL,
    description TEXT,
    original_filename VARCHAR(255) NOT NULL,
    user_id VARCHAR(64), -- For user isolation & IDOR defense
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_datasets_user_id ON datasets(user_id);

-- 2. Dataset Versions Table (Immutable version snapshots)
CREATE TABLE IF NOT EXISTS dataset_versions (
    id VARCHAR(36) PRIMARY KEY,
    dataset_id VARCHAR(36) NOT NULL REFERENCES datasets(id) ON DELETE CASCADE,
    version_number INT NOT NULL,
    parent_version_id VARCHAR(36) REFERENCES dataset_versions(id) ON DELETE SET NULL,
    storage_path VARCHAR(512) NOT NULL, -- Relative path to .parquet or .csv file
    file_format VARCHAR(16) NOT NULL DEFAULT 'parquet',
    row_count INT NOT NULL,
    column_count INT NOT NULL,
    file_size_bytes BIGINT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_dataset_version UNIQUE (dataset_id, version_number)
);

CREATE INDEX IF NOT EXISTS idx_dataset_versions_dataset_id ON dataset_versions(dataset_id);
CREATE INDEX IF NOT EXISTS idx_dataset_versions_parent_id ON dataset_versions(parent_version_id);

-- 3. Quality Reports Table (Multi-dimensional quality score per version)
CREATE TABLE IF NOT EXISTS quality_reports (
    id VARCHAR(36) PRIMARY KEY,
    version_id VARCHAR(36) NOT NULL REFERENCES dataset_versions(id) ON DELETE CASCADE,
    overall_score NUMERIC(5, 2) NOT NULL,
    grade VARCHAR(2) NOT NULL, -- 'A', 'B', 'C', 'D', 'F'
    grade_label VARCHAR(128) NOT NULL,
    completeness_score NUMERIC(5, 2) NOT NULL,
    validity_score NUMERIC(5, 2) NOT NULL,
    uniqueness_score NUMERIC(5, 2) NOT NULL,
    consistency_score NUMERIC(5, 2) NOT NULL,
    is_trustworthy BOOLEAN NOT NULL DEFAULT FALSE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    CONSTRAINT uq_version_quality_report UNIQUE (version_id)
);

CREATE INDEX IF NOT EXISTS idx_quality_reports_version_id ON quality_reports(version_id);
CREATE INDEX IF NOT EXISTS idx_quality_reports_grade ON quality_reports(grade);

-- 4. Quality Issues Table (Individual defects detected in a report)
CREATE TABLE IF NOT EXISTS quality_issues (
    id VARCHAR(36) PRIMARY KEY,
    report_id VARCHAR(36) NOT NULL REFERENCES quality_reports(id) ON DELETE CASCADE,
    category VARCHAR(64) NOT NULL, -- MISSING, DUPLICATE, INVALID_FORMAT, INVALID_RANGE, etc.
    severity VARCHAR(16) NOT NULL, -- CRITICAL, WARNING, INFO
    column_name VARCHAR(128),
    description TEXT NOT NULL,
    affected_count INT NOT NULL DEFAULT 0,
    affected_percentage NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    suggested_action TEXT,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_quality_issues_report_id ON quality_issues(report_id);
CREATE INDEX IF NOT EXISTS idx_quality_issues_category ON quality_issues(category);
CREATE INDEX IF NOT EXISTS idx_quality_issues_severity ON quality_issues(severity);

-- 5. Cleaning Jobs Table (Records lineage transformation between versions)
CREATE TABLE IF NOT EXISTS cleaning_jobs (
    id VARCHAR(36) PRIMARY KEY,
    source_version_id VARCHAR(36) NOT NULL REFERENCES dataset_versions(id) ON DELETE CASCADE,
    target_version_id VARCHAR(36) NOT NULL REFERENCES dataset_versions(id) ON DELETE CASCADE,
    total_operations INT NOT NULL DEFAULT 0,
    rows_modified INT NOT NULL DEFAULT 0,
    quality_score_delta NUMERIC(5, 2) NOT NULL DEFAULT 0.0,
    execution_log_json JSONB, -- Auditable log of all cleaning steps executed
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_cleaning_jobs_source_version ON cleaning_jobs(source_version_id);
CREATE INDEX IF NOT EXISTS idx_cleaning_jobs_target_version ON cleaning_jobs(target_version_id);
