# Evidence for Growth potential and market feasibility

- `www-build/index.html:0-5` → <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>2ndOpinionMD · Clinical Reasoning Engine</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  
- `server/eoh/module_50_policy.py:0-5` → # server/eoh/module_50_policy.py
"""
Module 50 – DxLandscapeFromEoH Policy Text

This file just exposes MODULE_TEXT so we can ingest it into rag_corpus
as part of eoh_gold_2025, exactly like modules 4
- `server/scripts/setup_clingen_actionability.py:0-5` → #!/usr/bin/env python3
import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

server_dir = Path(__file__).resolve().parent.parent
server_env_path = server_dir / ".env"
if s
- `public/index.html:0-5` → <!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <link rel="icon" href="%PUBLIC_URL%/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1" /
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
- `server/scripts/who_eml_sweeps.sql:0-5` → -- === ROUTE: high-confidence by dose_form (runs first) ===
UPDATE guidelines.who_eml_formulations f
SET route = COALESCE(f.route, CASE
  -- Specific sites
  WHEN f.dose_form ILIKE '%ophthalm%' OR f.d
- `server/scripts/ingest_orphanet.py:0-5` → #!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse, os, sys, zipfile, tempfile, time
from pathlib import Path
import xml.etree.ElementTree as ET

import psycopg2
from psycopg2.extras impo
- `server/eoh/router_llm.py:0-5` → # server/eoh/router_llm.py
"""
EoH LLM Router

Provides an LLM-based router that uses the EoH Reasoning Map (module index + routing recipes)
to select which EoH modules to use and where to look in the
- `server/eoh/module_49c_policy.py:0-5` → # server/eoh/module_49c_policy.py
#
# Module 49C — Diagnostic Update Reactor
#
# Encodes the labeling, learning and governance thresholds from Appendix F.49C.
# This module does NOT directly change pr
- `server/api/eoh_gap_retrieval.py:0-5` → # server/api/eoh_gap_retrieval.py

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

EOH_GAP_RETRIEVAL_SYSTEM_PRO
- `rag-demo-ui/index.html:0-5` → <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>2ndOpinionMD RAG Demo</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    * { box
- `database/sql/ehr_eoh_research_v2.sql:0-5` → -- =========================================
-- SCHEMA: ehr, eoh, research
-- v2.0 – Synthetic timelines + EoH + research
-- =========================================

CREATE SCHEMA IF NOT EXISTS ehr;
- `server/scripts/setup_complete_postgres.sh:0-5` → #!/bin/bash

set -e

echo "🚀 Setting up PostgreSQL with pgvector for 2ndOpinionMD-MVP..."

echo "📦 Installing PostgreSQL and dependencies..."
sudo apt update
sudo apt install -y postgresql postgresql-
- `frontend/react/src/utils/ethosOfHealth.js:0-5` → export const ZONES = {
  ZONE_1: { id: 1, name: "Zone 1", description: "Stable Terrain" },
  ZONE_2: { id: 2, name: "Zone 2", description: "Mild Fluctuation" },
  ZONE_3: { id: 3, name: "Zone 3", desc
- `server/api/app_postgres.py:0-5` → # server/api/app_postgres.py
import os
import json
import logging
import sys
import traceback
import re
from contextlib import asynccontextmanager
from typing import List, Dict, Any, Optional
from pat
- `frontend/react/src/utils/sampleAnalysisData.js:0-5` → export const sampleAnalysisData = {
  analysis: "The patient reports symptoms of fatigue and headache, which are common but nonspecific and could be indicative of a range of conditions including autoi
- `frontend/react/src/components/AIResponse/AIResponseDisplay.js:0-5` → import React, { useState } from 'react';
import PropTypes from 'prop-types';
import { downloadPdfReport } from '../../utils/pdfGenerator';
import './AIResponseDisplay.css';

const AIResponseDisplay = 
- `scripts/inspect_env_for_docker.sh:0-5` → #!/usr/bin/env bash
set -euo pipefail

# Adjust these if needed
PROJECT_ROOT="$(pwd)"
DB_NAME="2ndopinionmd"

OUT_DIR="${PROJECT_ROOT}/docker_env_report"
mkdir -p "$OUT_DIR"

log() {
  echo "[$(date +
- `frontend/react/src/utils/pdfGenerator.js:0-5` → import jsPDF from 'jspdf';

/**
 * Generates a PDF report from the diagnostic results
 * @param {Array} diagnosticResults - Array of diagnostic results
 * @returns {Promise} - Promise that resolves wh
- `database/sql/add_orphanet_indexes.sql:0-5` → -- Extra useful btree indexes (safe if already exist)
CREATE INDEX IF NOT EXISTS orphanet_phenos_orpha_idx ON ontology.orphanet_phenotype_links (orpha_code);
CREATE INDEX IF NOT EXISTS orphanet_phenos
- `server/scripts/report_disgenet_pdf.py:0-5` → #!/usr/bin/env python3
# server/scripts/report_disgenet_pdf.py
import os
from report_common import (
    connect, q, build_doc,
    P, H2, BODY, TableFromRows, Spacer, ai_analyze
)

OUT = "db_integrit
- `frontend/react/src/components/PricingSection/PricingSection.jsx:0-5` → import React from 'react';
import './PricingSection.css';

const PricingSection = () => {
  const pricingPlans = [
    {
      name: 'Basic',
      price: 'Free Beta-Testing (give us feedback!)',
    
- `physionet.org/files/mimiciii/1.4/index.html:0-5` → <html>
<head><title>Index of /protected/published-projects/mimiciii/1.4/</title></head>
<body>
<h1>Index of /protected/published-projects/mimiciii/1.4/</h1><hr><pre><a href="../">../</a>
<a href="ADMI
- `server/eoh/modules/m13_flare_risk.py:0-5` → # server/eoh/modules/m13_flare_risk.py

from __future__ import annotations

from typing import Dict, Any


MODULE_NAME = "M13_flare_risk"
MODULE_VERSION = "0.1.0-M0"


def compute_flare_risk(features:
- `server/scripts/disgenet_plan_today.sh:0-5` → #!/usr/bin/env bash
set -euo pipefail

# Inputs you already keep up to date
UNIVERSE="data/autoimmune_gene_ids.clean"     # full candidate list (Entrez IDs)
DONE_IDS="data/disgenet_done.ids"          
- `database/schemas/setup_cdc_opioid.sql:0-5` → -- 2.1 Raw docs + normalized sections
CREATE SCHEMA IF NOT EXISTS guidelines;

CREATE TABLE IF NOT EXISTS guidelines.cdc_docs (
  doc_id         bigserial PRIMARY KEY,
  source_key     text NOT NULL, 
- `database/sql/integrity_icd.sql:0-5` → \echo '-- ICD presence flags'
SELECT
  (to_regclass('ontology.icd10cm') IS NOT NULL)  AS has_icd10cm,
  (to_regclass('ontology.icd11')  IS NOT NULL)   AS has_icd11,
  (to_regclass('ontology.snomed_map
- `server/scripts/report_snomed_pdf.py:0-5` → #!/usr/bin/env python3
import argparse
from report_common import q, connect, build_doc, TableFromRows, P, H2
from reportlab.lib.units import inch

def flow(story, content_width):
    conn = connect()

- `server/scripts/who_eml_form_backfill.sql:0-5` → -- ROUTE inference with JOIN to medicines (idempotent)
UPDATE guidelines.who_eml_formulations f
SET route = COALESCE(f.route, CASE
  WHEN f.dose_form ILIKE '%tablet%' OR f.dose_form ILIKE '%capsule%' 
- `server/scripts/ingest_clingen_actionability.py:0-5` → #!/usr/bin/env python3
import os, sys, csv, gzip, re
from datetime import datetime
from report_common import connect, q

# Map various header spellings to our canonical columns
HEADER_MAP = {
  'gene_
- `frontend/react/index.js:0-5` → import React from 'react';
import ReactDOM from 'react-dom/client';
import './index.css';
import App from './App';
import reportWebVitals from './reportWebVitals';
import ErrorBoundary from './compone
- `server/api/kg.py:0-5` → import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseMo
- `physionet.org/files/mimiciv/2.2/hosp/index.html:0-5` → <html>
<head><title>Index of /protected/published-projects/mimiciv/2.2/hosp/</title></head>
<body>
<h1>Index of /protected/published-projects/mimiciv/2.2/hosp/</h1><hr><pre><a href="../">../</a>
<a hr
- `server/utils/constants.js:0-5` → exports.SYMPTOMS = [
  { value: 'fatigue', label: 'Fatigue' },
  { value: 'joint_pain', label: 'Joint Pain' },
  { value: 'brain_fog', label: 'Brain Fog' },
  { value: 'headache', label: 'Headache' },
- `server/api/clingen_actionability_routes.py:0-5` → from fastapi import APIRouter, Query, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from 
- `frontend/react/test_diagnosis_display.html:0-5` → <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Diagnosis Display</title>
    <style>
    
- `frontend/react/src/components/journal/JournalResponse.jsx:0-5` → import React from 'react';
import PropTypes from 'prop-types';
import JournalAnalysisDisplay from './JournalAnalysisDisplay';
import './JournalResponse.css';
import '../../styles/Journal.css';

const 
- `frontend/react/src/utils/constants.js:0-5` → export const SYMPTOMS = [
  { value: 'fatigue', label: 'Fatigue' },
  { value: 'joint_pain', label: 'Joint Pain' },
  { value: 'brain_fog', label: 'Brain Fog' },
  { value: 'headache', label: 'Headach
- `database/sql/setup_knowledgegraph.sql:0-5` → CREATE DATABASE knowledgegraph;

\c knowledgegraph;

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS vector;

DO $$
BEGIN
    IF NOT 
- `frontend/react/src/utils/openaiService.js:0-5` → import axios from 'axios';
import { generateEthosPrompt, ZONES, STAX_LEVELS } from './ethosOfHealth';
import { calculateAgeFromBirthdate } from './formatData';
import { getApiUrl, API_ENDPOINTS } from
- `server/scripts/report_orphanet_pdf.py:0-5` → #!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, argparse
from reportlab.lib.units import inch
from report_common import (
    connect, q, build_doc, TableFromRows, P, H2, ai_analyze, BODY
)
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
- `server/scripts/audit_nullables.py:0-5` → #!/usr/bin/env python3
"""
Audit script to detect schema misalignments between database and SQLAlchemy models
Run from repo root: PYTHONPATH=. python server/scripts/audit_nullables.py
"""
import async
- `server/utils/diagnosticUtils.js:0-5` → const { POSSIBLE_DIAGNOSES } = require('./constants');

/**
 * Formats symptom data from the request
 * @param {Object} formData - Form data from the request
 * @returns {Object} - Formatted data
 */

- `server/test.sh:0-5` → GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${YELLOW}Starting 2ndOpinionMD Express Server Tests${NC}"

echo -e "\n${YELLOW}Checking MongoDB status...${NC}
- `database/sql/ddl_orphanet.sql:0-5` → CREATE SCHEMA IF NOT EXISTS ontology;
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- Core diseases table
CREATE TABLE IF NOT EXISTS ontology.orphanet_diseases (
  orpha_code   TEXT PRIMARY KEY,          
- `server/scripts/rag_regression_hf_glp1.py:0-5` → #!/usr/bin/env python3
import asyncio
import json
import sys

import httpx

API_BASE = "https://2ndopinionmd.ai"

HF_GLP1_QUERY = (
    "In adults with heart failure (with and without type 2 diabetes)
- `database/schemas/setup_disgenet_schema.sql:0-5` → -- database/schemas/setup_disgenet_schema.sql
BEGIN;

CREATE SCHEMA IF NOT EXISTS molecular;

-- Ensure table exists
CREATE TABLE IF NOT EXISTS molecular.disgenet_associations (
  assoc_id text  -- wi
- `server/models/Report.js:0-5` → /**
 * Report model for in-memory storage with ethos of health model integration
 * In a production environment, this would be replaced with a database model
 */
class Report {
  constructor() {
    t
- `frontend/react/src/utils/apiConfig.js:0-5` → const ENDPOINTS = {
  AUTH: '/auth',
  AUTH_TOKEN: '/auth/token',
  AUTH_ME: '/auth/me',
  JOURNAL: '/journal',
  DIAGNOSE: '/diagnose',
  REPORTS: '/reports',
  HEALTH: '/health'
};

function readBas
- `frontend/react/src/components/journal/JournalAnalysisDisplay.js:0-5` → import React from 'react';
import { parseJournalAnalysis } from '../../utils/parseJournalAnalysis';
import DiagnosisTable from './DiagnosisTable';
import DebugBlock from '../common/DebugBlock';
import
- `server/ann/diagnostic.py:0-5` → """
Diagnostic Landscape Engine
Location: server/ann/diagnostic.py
Version: v100 (Cipher + Devin Method)

This module implements the diagnostic landscape estimator using ANN search.

Output MUST follo
- `server/scripts/ingest_ethos_of_health.py:0-5` → #!/usr/bin/env python3
"""
Ethos of Health Ingestion Script

Purpose:
  - Upsert the Ethos of Health framework documents into public.rag_corpus
    as a first-class RAG source (source='ethos_model').

- `server/scripts/debug_llm_gap.py:0-5` → # server/scripts/debug_llm_gap.py

import asyncio
import os
import json

from openai import OpenAI

from server.api.rag_stream_routes import _llm_expand_terms_for_slot  # adjust import if it lives els
- `frontend/react/src/components/journal/JournalList.js:0-5` → import React, { useState, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import { apiFetch } from '../../utils/apiClient';
import { downloadJournalTimelin
- `database/sql/cdc_assert.sql:0-5` → DO $$
DECLARE
  miss      int;
  ann       boolean;
  no_embed  int;
BEGIN
  -- R1..R12 present?
  SELECT COUNT(*) INTO miss
  FROM (SELECT unnest(ARRAY['R1','R2','R3','R4','R5','R6','R7','R8','R9','R
- `server/scripts/report_who_audit_pdf.py:0-5` → #!/usr/bin/env python3
# WHO EML / AWaRe / Committee — Audit & Integrity PDF
import os, json
from report_common import (
    connect, q, build_doc, P, H2, BODY, TableFromRows, Spacer, ai_analyze
)

OU
- `server/eoh/module_index.py:0-5` → # server/eoh/module_index.py
"""
EoH Module Index

Defines the MODULE_INDEX dictionary containing all EoH modules used for
flare prediction, interpretation, and care planning. Based on Andras's
"EoH R
- `server/templates/verification.html:0-5` → <!DOCTYPE html>
<html>
<head>
    <meta charset="utf-8">
    <title>Verify Your Email - 2ndOpinionMD</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            line-hei
- `./fmp/agents/global_triage_agent.py:0-5` → - CODER: keywords {"implement", "feature", "task", "build", "add", "code"}
- `./fmp/agents/global_triage_agent.py:0-5` → coder_keys = {"implement", "feature", "task", "build", "add", "code"}
