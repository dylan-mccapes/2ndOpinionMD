# Evidence for Standout behaviors and system capabilities

- `frontend/react/src/utils/ethosOfHealth.js:0-5` → export const ZONES = {
  ZONE_1: { id: 1, name: "Zone 1", description: "Stable Terrain" },
  ZONE_2: { id: 2, name: "Zone 2", description: "Mild Fluctuation" },
  ZONE_3: { id: 3, name: "Zone 3", desc
- `database/sql/15_disgenet_audit.sql:0-5` → -- 15_disgenet_audit.sql  (save anywhere / run in psql)
WITH base AS (
  SELECT *
  FROM   molecular.disgenet_associations
),
tot AS (
  SELECT
    COUNT(*)                                AS rows,
   
- `www-build/index.html:0-5` → <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>2ndOpinionMD · Clinical Reasoning Engine</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  
- `frontend/react/src/components/AIResponse/AIResponseDisplay.css:0-5` → .ai-response-container {
  padding: 24px;
  max-width: 800px;
  margin: 0 auto;
}

.response-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}
- `database/sql/16_gwas_audit.sql:0-5` → -- database/sql/16_gwas_audit.sql
WITH b AS (
  SELECT * FROM molecular.gwas_hits
),
t AS (
  SELECT COUNT(*)::int AS rows FROM b
),
nulls AS (
  SELECT
    COUNT(*) FILTER (WHERE disease_trait IS NUL
- `frontend/react/src/components/journal/JournalAnalysisDisplay.css:0-5` → .ai-analysis {
  background: white;
  border-radius: 8px;
  padding: 1.5rem;
  margin: 1rem 0;
  box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
}

.ai-analysis-header {
  display: flex;
  justify-content: 
- `frontend/react/test_diagnosis_display.html:0-5` → <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Diagnosis Display</title>
    <style>
    
- `database/sql/17_neurolex_audit.sql:0-5` → -- database/sql/17_neurolex_audit.sql
-- Emits one JSON row with overall + core stats.

WITH
presence AS (
  SELECT
    (to_regclass('ontology.neurolex') IS NOT NULL)        AS has_terms,
    (to_regc
- `scripts/inspect_env_for_docker.sh:0-5` → #!/usr/bin/env bash
set -euo pipefail

# Adjust these if needed
PROJECT_ROOT="$(pwd)"
DB_NAME="2ndopinionmd"

OUT_DIR="${PROJECT_ROOT}/docker_env_report"
mkdir -p "$OUT_DIR"

log() {
  echo "[$(date +
- `server/test.sh:0-5` → GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting 2ndOpinionMD Express Server Tests${NC}"

echo -e "\n${YELLOW}Checking MongoDB status...${NC}
- `database/sql/integrity_icd.sql:0-5` → \echo '-- ICD presence flags'
SELECT
  (to_regclass('ontology.icd10cm') IS NOT NULL)  AS has_icd10cm,
  (to_regclass('ontology.icd11')  IS NOT NULL)   AS has_icd11,
  (to_regclass('ontology.snomed_map
- `frontend/react/App.css:0-5` → .App {
  display: flex;
  flex-direction: column;
  min-height: 100vh;
}

.App-header {
  background-color: var(--color-primary);
  color: white;
  padding: 16px 0;
  text-align: center;
}

.App-heade
- `server/eoh/module_50_policy.py:0-5` → # server/eoh/module_50_policy.py
"""
Module 50 – DxLandscapeFromEoH Policy Text

This file just exposes MODULE_TEXT so we can ingest it into rag_corpus
as part of eoh_gold_2025, exactly like modules 4
- `rag-demo-ui/index.html:0-5` → <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>2ndOpinionMD RAG Demo</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    * { box
- `server/scripts/setup_clingen_actionability.py:0-5` → #!/usr/bin/env python3
import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

server_dir = Path(__file__).resolve().parent.parent
server_env_path = server_dir / ".env"
if s
- `server/scripts/report_who_audit_pdf.py:0-5` → #!/usr/bin/env python3
# WHO EML / AWaRe / Committee — Audit & Integrity PDF
import os, json
from report_common import (
    connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze
)

OU
- `server/scripts/report_disgenet_pdf.py:0-5` → #!/usr/bin/env python3
# server/scripts/report_disgenet_pdf.py
import os
from report_common import (
    connect, q, build_doc,
    P, H2, BODY, TableFromRows, Spacer, ai_analyze
)

OUT = "db_integrit
- `frontend/react/src/components/SecurityBadge/SecurityBadge.css:0-5` → .security-badge {
  display: flex;
  align-items: center;
  background-color: rgba(60, 125, 136, 0.1);
  border-radius: 6px;
  padding: 8px 12px;
  margin: 16px 0;
  border-left: 3px solid var(--color
- `server/scripts/coding_qa.sh:0-5` → #!/usr/bin/env bash

set -euo pipefail

BASE_URL="${BASE_URL:-https://2ndopinionmd.ai}"

run_test() {
  local name="$1"
  local query="$2"
  local sources="$3"
  local limit="$4"
  local ctx_k="$5"

 
- `server/scripts/report_orphanet_pdf.py:0-5` → #!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, argparse
from reportlab.lib.units import inch
from report_common import (
    connect, q, build_doc, TableFromRows, P, H2, ai_analyze, BODY
)
- `database/sql/20_cdc_audit.sql:0-5` → WITH
docs AS (SELECT * FROM guidelines.cdc_docs),
sections AS (SELECT * FROM guidelines.cdc_sections),
rag AS (SELECT * FROM public.rag_corpus WHERE source = 'cdc_opioid'),
xref AS (SELECT * FROM guid
- `server/scripts/report_panelapp_pdf.py:0-5` → #!/usr/bin/env python3
"""
PanelApp Integrity / Audit PDF

- Verdict rules:
  * FAIL if table missing
  * WARN if table present but 0 rows
  * WARN if critical blanks >5% (critical = gene_symbol + con
- `server/scripts/report_loinc_rxnorm_pdf.py:0-5` → #!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import argparse
import psycopg2
from psycopg2.extras import RealDictCursor
from reportlab.lib.units import inch
from report_common import (
  
- `frontend/react/src/components/SymptomIntake/SymptomIntakeForm.css:0-5` → .symptom-intake-container {
  padding: 24px;
  max-width: 800px;
  margin: 0 auto;
}

.form-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}

- `frontend/react/src/components/AIResponse/AIResponseDisplay.js:0-5` → import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { downloadPdfReport } from '../../utils/pdfGenerator';
import './AIResponseDisplay.css';

const AIResponseDisplay = 
- `www-build/rag-demo/index.html:0-5` → <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>2ndOpinionMD · RAG Stream Demo</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
  
- `server/eoh/module_index.py:0-5` → # server/eoh/module_index.py
"""
EoH Module Index

Defines the MODULE_INDEX dictionary containing all EoH modules used for
flare prediction, interpretation, and care planning. Based on Andras's
"EoH R
- `database/sql/integrity_report.sql:0-5` → -- Human-readable integrity snapshot (one result set)
WITH m AS (
  SELECT 'db'::text section, 'size_pretty'::text metric,
         pg_size_pretty(pg_database_size(current_database()))::text AS value,
- `18_nice_audit.sql:0-5` → -- One-row JSON-ish result describing NICE/CKS coverage & health.

WITH has_chunks_tbl AS (
  SELECT to_regclass('public.rag_corpus_chunks') IS NOT NULL AS exists
),
docs AS (
  SELECT *
  FROM guidel
- `frontend/react/src/components/TestimonialCarousel/TestimonialCarousel.css:0-5` → .testimonial-section {
  padding: var(--spacing-section) 24px;
  background-color: var(--color-bg-light);
  text-align: center;
  position: relative;
  overflow: hidden;
}

.testimonial-container {
  
- `server/scripts/report_gwas_pdf.py:0-5` → #!/usr/bin/env python3
import os, json, pathlib
from report_common import (
    connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze
)

OUT = "db_integrity_reports/16_gwas.pdf"
SQL_PA
- `server/scripts/report_va_audit_pdf.py:0-5` → #!/usr/bin/env python3
# VA/DoD Guidelines — Audit & Integrity PDF
import os
from report_common import (
    connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze
)

OUT = "db_integrit
- `frontend/react/src/styles/SplashPage.css:0-5` → .splash-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 2rem;
  background: linear-gradient(135deg, #f5f7fa 0%,
- `sql/autoimmune_ranked.sql:0-5` → WITH src AS (
  SELECT gene_symbol,
         panel_name,
         coalesce(confidence_level,'') AS confidence_level
  FROM molecular.gene_panels
  WHERE coalesce(signed_off, true)
    AND (
      pane
- `frontend/react/src/utils/openaiService.js:0-5` → import axios from 'axios';
import { generateEthosPrompt, ZONES, STAX_LEVELS } from './ethosOfHealth';
import { calculateAgeFromBirthdate } from './formatData';
import { getApiUrl, API_ENDPOINTS } from
- `server/api/coding_routes_with_note.py:0-5` → # server/api/coding_routes.py (with Note appended to PDF + minor fixes)
# --- add imports at the top ---
import os, json, re, io, textwrap
from typing import Any, Dict, List, Optional, Iterable
from f
- `database/sql/18_nice_audit.sql:0-5` → WITH has_chunks_tbl AS (
  SELECT to_regclass('public.rag_corpus_chunks') IS NOT NULL AS exists
),
docs AS (
  SELECT * FROM guidelines.docs WHERE source_key = 'nice'
),
sections AS (
  SELECT s.* FRO
- `server/scripts/ingest_ethos_of_health.py:0-5` → #!/usr/bin/env python3
"""
Ethos of Health Ingestion Script

Purpose:
  - Upsert the Ethos of Health framework documents into public.rag_corpus
    as a first-class RAG source (source='ethos_model').

- `frontend/react/src/App.js:0-5` → import React, { useState, useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate, Link, useNavigate } from 'react-router-dom';
import './App.css';
import './styles/GlobalS
- `server/scripts/report_hpo_pdf.py:0-5` → #!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, argparse, datetime
from reportlab.lib.units import inch
from report_common import (
    connect, q, build_doc, TableFromRows, P, H2, ai_analy
- `server/eoh/timeline_summarizer.py:0-5` → from __future__ import annotations

import json
import logging
import math
import os
import textwrap
from dataclasses import dataclass
from typing import Any, Dict, List
from inspect import iscoroutin
- `database/schemas/setup_cdc_opioid.sql:0-5` → -- 2.1 Raw docs + normalized sections
CREATE SCHEMA IF NOT EXISTS guidelines;

CREATE TABLE IF NOT EXISTS guidelines.cdc_docs (
  doc_id         bigserial PRIMARY KEY,
  source_key     text NOT NULL, 
- `server/scripts/report_clingen_aci_pdf.py:0-5` → #!/usr/bin/env python3
import os, sys, math, datetime as dt
from typing import List, Dict, Any, Tuple
from report_common import connect, q, build_doc, P, H2, BODY, SMALL, TableFromRows, Spacer, ai_ana
- `frontend/react/src/components/ReportOverview/ReportOverview.css:0-5` → .report-overview {
  padding: 60px 24px;
  background-color: white;
  max-width: 1200px;
  margin: 0 auto;
}

.report-overview h2 {
  font-size: 32px;
  margin-bottom: 20px;
  color: var(--color-text-
- `database/sql/add_neurolex_indexes.sql:0-5` → WITH x AS (
  SELECT ilx_id,
         split_part(value, ':', 1) AS system,
         split_part(value, ':', 2) AS code
  FROM ontology.neurolex_annotations
  WHERE prop_label = 'hasDbXref'
)
-- Example
- `server/scripts/report_mimic_pdf.py:0-5` → #!/usr/bin/env python3
import os, sys
from datetime import datetime
from report_common import (
    connect, q, build_doc, TableFromRows, P, H2, BODY, ai_analyze
)
from reportlab.platypus import Space
- `server/scripts/report_snomed_pdf.py:0-5` → #!/usr/bin/env python3
import argparse
from report_common import q, connect, build_doc, TableFromRows, P, H2
from reportlab.lib.units import inch

def flow(story, content_width):
    conn = connect()

- `database/sql/integrity_snomed_json.sql:0-5` → \set ON_ERROR_STOP on
WITH present AS (
  SELECT
    EXISTS (SELECT 1 FROM information_schema.tables WHERE table_schema='ontology' AND table_name='concepts')        AS has_concepts,
    EXISTS (SELECT
- `frontend/react/src/components/journal/JournalAnalysisDisplay.js:0-5` → import React from 'react';
import { parseJournalAnalysis } from '../../utils/parseJournalAnalysis';
import DiagnosisTable from './DiagnosisTable';
import DebugBlock from '../common/DebugBlock';
import
- `database/schemas/ehr_mimic4.sql:0-5` → -- Schema
CREATE SCHEMA IF NOT EXISTS ehr_mimic4;

-- ======================
-- HOSP module
-- ======================
CREATE TABLE IF NOT EXISTS ehr_mimic4.patients (
  subject_id           BIGINT PRI
- `server/scripts/train_ap_transformers.py:0-5` → import os, json, argparse, numpy as np
from datasets import load_dataset
from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                          DataCollatorWithPadding,
- `load_unified_icd.sh:0-5` → #!/bin/bash

set -e  # Exit on any error

echo "🚀 Starting Unified ICD Loader Pipeline..."
echo "================================================"

if ! pg_isready -q; then
    echo "❌ PostgreSQL is n
- `frontend/react/src/components/PricingSection/PricingSection.css:0-5` → .pricing-section {
  padding: 80px 24px;
  background-color: var(--color-bg-light);
}

.pricing-container {
  max-width: 1200px;
  margin: 0 auto;
  text-align: center;
}

.pricing-section h2 {
  font
- `server/eoh/router_llm.py:0-5` → # server/eoh/router_llm.py
"""
EoH LLM Router

Provides an LLM-based router that uses the EoH Reasoning Map (module index + routing recipes)
to select which EoH modules to use and where to look in the
- `server/api/clingen_actionability_routes.py:0-5` → from fastapi import APIRouter, Query, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from 
- `frontend/react/src/styles/Journal.css:0-5` → /* Journal Styles */
.journal-form-container,
.journal-list-container,
.journal-detail-container {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem;
  background-color: white;
  border-radius: 8
- `database/schemas/clingen_actionability.sql:0-5` → CREATE SCHEMA IF NOT EXISTS clingen;

-- Core summary (what your routes file reads)
CREATE TABLE IF NOT EXISTS clingen.actionability_summary (
  cohort                  text NOT NULL,             -- '
- `server/api/stream_config.py:0-5` → # server/api/stream_config.py

import os
import re
from typing import Any, Dict, List, Set, Optional
import json
from openai import OpenAI
import textwrap

# ------------------------------------------
- `server/api/citation_governance.py:0-5` → # server/api/citation_governance.py
from __future__ import annotations
from typing import Any, Dict, List, Optional
import re, datetime

AUTHORITATIVE = {"icd10cm","icd10-cm","icd11","snomed","snomed 
- `./fmp/agents/global_triage_agent.py:0-5` → - CODER: keywords {"implement", "feature", "task", "build", "add", "code"}
- `./fmp/agents/global_triage_agent.py:0-5` → coder_keys = {"implement", "feature", "task", "build", "add", "code"}
