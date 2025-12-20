# Evidence for Competitor landscape and differentiators

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
- `server/timeline/seed_diagnostic_landscapes.py:0-5` → # server/timeline/seed_diagnostic_landscapes.py
from __future__ import annotations
import asyncio
import json
import asyncpg
from datetime import datetime

DSN = "postgresql://localhost/2ndopinionmd"

- `server/scripts/train_ap_transformers.py:0-5` → import os, json, argparse, numpy as np
from datasets import load_dataset
from transformers import (AutoTokenizer, AutoModelForSequenceClassification,
                          DataCollatorWithPadding,
- `server/eoh/modules/m17_diagnostic_landscape.py:0-5` → # server/eoh/modules/m17_diagnostic_landscape.py

from __future__ import annotations

from typing import Dict, Any


MODULE_NAME = "M17_diagnostic_landscape"
MODULE_VERSION = "0.1.0-M0"


def compute_
- `server/eoh/router_llm.py:0-5` → # server/eoh/router_llm.py
"""
EoH LLM Router

Provides an LLM-based router that uses the EoH Reasoning Map (module index + routing recipes)
to select which EoH modules to use and where to look in the
- `frontend/react/src/components/TestimonialCarousel/TestimonialCarousel.css:0-5` → .testimonial-section {
  padding: var(--spacing-section) 24px;
  background-color: var(--color-bg-light);
  text-align: center;
  position: relative;
  overflow: hidden;
}

.testimonial-container {
  
- `server/api/kg.py:0-5` → import os
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path

from fastapi import APIRouter, HTTPException, Body, Query
from pydantic import BaseMo
- `server/timeline/engine.py:0-5` → from __future__ import annotations

import os
import asyncio
import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, List, Optional, Sequence

import 
- `server/eoh/module_50_runtime.py:0-5` → # server/eoh/module_50_runtime.py
"""
Runtime scaffolding for Module 50 – DxLandscapeFromEoH.

This wraps Andras's spec in Python dataclasses and provides a thin async
entrypoint that other code (e.g.
- `database/sql/integrity_icd.sql:0-5` → \echo '-- ICD presence flags'
SELECT
  (to_regclass('ontology.icd10cm') IS NOT NULL)  AS has_icd10cm,
  (to_regclass('ontology.icd11')  IS NOT NULL)   AS has_icd11,
  (to_regclass('ontology.snomed_map
- `database/sql/15_disgenet_audit.sql:0-5` → -- 15_disgenet_audit.sql  (save anywhere / run in psql)
WITH base AS (
  SELECT *
  FROM   molecular.disgenet_associations
),
tot AS (
  SELECT
    COUNT(*)                                AS rows,
   
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
- `frontend/react/src/components/PricingSection/PricingSection.jsx:0-5` → import React from 'react';
import './PricingSection.css';

const PricingSection = () => {
  const pricingPlans = [
    {
      name: 'Basic',
      price: 'Free Beta-Testing (give us feedback!)',
    
- `server/eoh/module_index.py:0-5` → # server/eoh/module_index.py
"""
EoH Module Index

Defines the MODULE_INDEX dictionary containing all EoH modules used for
flare prediction, interpretation, and care planning. Based on Andras's
"EoH R
- `database/sql/mimic_indexes.sql:0-5` → -- database/sql/mimic_indexes.sql
-- BM25 GIN over ts per-source
CREATE INDEX IF NOT EXISTS rag_corpus_ts_m4dx_gin   ON public.rag_corpus USING GIN (ts) WHERE source='mimic4_dx';
CREATE INDEX IF NOT E
- `rag-demo-ui/index.html:0-5` → <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>2ndOpinionMD RAG Demo</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
    * { box
- `frontend/react/src/utils/ethosOfHealth.js:0-5` → export const ZONES = {
  ZONE_1: { id: 1, name: "Zone 1", description: "Stable Terrain" },
  ZONE_2: { id: 2, name: "Zone 2", description: "Mild Fluctuation" },
  ZONE_3: { id: 3, name: "Zone 3", desc
- `server/eoh/timeline_summarizer.py:0-5` → from __future__ import annotations

import json
import logging
import math
import os
import textwrap
from dataclasses import dataclass
from typing import Any, Dict, List
from inspect import iscoroutin
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
- `frontend/react/src/components/layout/Footer.css:0-5` → .footer {
  background-color: var(--color-bg);
  padding: 24px 0;
  border-top: 1px solid var(--color-border);
}

.footer-container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 16px;
}

.foot
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
- `server/scripts/who_eml_sweeps.sql:0-5` → -- === ROUTE: high-confidence by dose_form (runs first) ===
UPDATE guidelines.who_eml_formulations f
SET route = COALESCE(f.route, CASE
  -- Specific sites
  WHEN f.dose_form ILIKE '%ophthalm%' OR f.d
- `server/api/stream_config.py:0-5` → # server/api/stream_config.py

import os
import re
from typing import Any, Dict, List, Set, Optional
import json
from openai import OpenAI
import textwrap

# ------------------------------------------
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
- `www-build/rag-demo/index.html:0-5` → <!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8" />
  <title>2ndOpinionMD · RAG Stream Demo</title>
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <style>
  
- `server/api/stream_router.py:0-5` → # server/api/stream_router.py

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from openai import OpenAI
import json

from .stream_config import CHAT_MODEL_UTIL, GUIDEL
- `server/api/clingen_actionability_routes.py:0-5` → from fastapi import APIRouter, Query, Depends, HTTPException, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from 
- `frontend/react/public/index.html:0-5` → <!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <link rel="icon" href="%PUBLIC_URL%/favicon.ico" />
    <meta name="viewport" content="width=device-width, initial-scale=1" /
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
- `database/sql/icd_combined_audit.sql:0-5` → SET search_path = public, ontology;
\pset tuples_only on

WITH rag_icd AS (
  SELECT source, source_id, meta, embedding
  FROM public.rag_corpus
  WHERE source = 'icd10cm'
),
codes_from_table(n) AS (

- `server/eoh/module_49c_policy.py:0-5` → # server/eoh/module_49c_policy.py
#
# Module 49C — Diagnostic Update Reactor
#
# Encodes the labeling, learning and governance thresholds from Appendix F.49C.
# This module does NOT directly change pr
- `database/sql/22_icd_audit.sql:0-5` → SELECT jsonb_build_object(
  'presence', jsonb_build_object(
    'has_rag', EXISTS(SELECT 1 FROM public.rag_corpus WHERE source IN ('icd10cm','icd11'))
  ),
  'icd10cm', jsonb_build_object(
    'rows'
- `scripts/inspect_env_for_docker.sh:0-5` → #!/usr/bin/env bash
set -euo pipefail

# Adjust these if needed
PROJECT_ROOT="$(pwd)"
DB_NAME="2ndopinionmd"

OUT_DIR="${PROJECT_ROOT}/docker_env_report"
mkdir -p "$OUT_DIR"

log() {
  echo "[$(date +
- `frontend/react/src/styles/SplashPage.css:0-5` → .splash-container {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  padding: 2rem;
  background: linear-gradient(135deg, #f5f7fa 0%,
- `www-build/rag-demo/static/js/453.1754d0d8.chunk.js:0-5` → "use strict";(self.webpackChunk_2ndopinionmd_react=self.webpackChunk_2ndopinionmd_react||[]).push([[453],{453:(e,t,n)=>{n.r(t),n.d(t,{getCLS:()=>y,getFCP:()=>g,getFID:()=>C,getLCP:()=>P,getTTFB:()=>D}
- `database/sql/17_neurolex_audit.sql:0-5` → -- database/sql/17_neurolex_audit.sql
-- Emits one JSON row with overall + core stats.

WITH
presence AS (
  SELECT
    (to_regclass('ontology.neurolex') IS NOT NULL)        AS has_terms,
    (to_regc
- `server/scripts/setup_clingen_actionability.py:0-5` → #!/usr/bin/env python3
import os
import psycopg2
from dotenv import load_dotenv
from pathlib import Path

server_dir = Path(__file__).resolve().parent.parent
server_env_path = server_dir / ".env"
if s
- `database/sql/17_neurolex_core.sql:0-5` → -- database/sql/17_neurolex_core.sql
-- Define a "core" slice of NeuroLex terms (exclude CDE/forms + UI schema bits).
-- Idempotent: safe to re-run.

CREATE SCHEMA IF NOT EXISTS ontology;

-- Core sub
- `server/scripts/report_orphanet_pdf.py:0-5` → #!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, argparse
from reportlab.lib.units import inch
from report_common import (
    connect, q, build_doc, TableFromRows, P, H2, ai_analyze, BODY
)
- `server/timeline/seed_landscape_events_from_state.py:0-5` → # server/timeline/seed_landscape_events_from_state.py

from __future__ import annotations

import os
from typing import Dict, Any

import psycopg2
from psycopg2.extras import RealDictCursor, Json


de
- `frontend/react/test_diagnosis_display.html:0-5` → <!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Test Diagnosis Display</title>
    <style>
    
- `database/sql/mimic_rag_upsert.sql:0-5` → -- database/sql/mimic_rag_upsert.sql
CREATE EXTENSION IF NOT EXISTS pg_trgm;

-- ── (A) Remove vocab-only dx/proc rows (no hadm_id in meta) ─────────
DELETE FROM public.rag_corpus
WHERE source IN ('mi
- `server/scripts/ingest_hpo_json.py:0-5` → #!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json, argparse, re
import psycopg2, psycopg2.extras

def connect():
    dsn = os.environ.get("SYNC_DATABASE_URL", "postgresql://2ndopinionmd@
- `database/sql/integrity_icd_json.sql:0-5` → WITH map AS (
  SELECT
    COUNT(*)                           AS rows_all,
    COUNT(*) FILTER (WHERE NULLIF(trim(map_target),'') IS NOT NULL) AS rows_with_target,
    COUNT(DISTINCT NULLIF(trim(map_t
- `server/scripts/report_clingen_aci_pdf.py:0-5` → #!/usr/bin/env python3
import os, sys, math, datetime as dt
from typing import List, Dict, Any, Tuple
from report_common import connect, q, build_doc, P, H2, BODY, SMALL, TableFromRows, Spacer, ai_ana
- `database/sql/20_cdc_audit.sql:0-5` → WITH
docs AS (SELECT * FROM guidelines.cdc_docs),
sections AS (SELECT * FROM guidelines.cdc_sections),
rag AS (SELECT * FROM public.rag_corpus WHERE source = 'cdc_opioid'),
xref AS (SELECT * FROM guid
- `server/scripts/ingest_panelapp.py:0-5` → import os, sys, json, time, re, requests, psycopg2
from psycopg2.extras import execute_values
from urllib.parse import urlencode
from requests.adapters import HTTPAdapter
from urllib3.util.retry impor
- `database/sql/ehr_eoh_research_v2.sql:0-5` → -- =========================================
-- SCHEMA: ehr, eoh, research
-- v2.0 – Synthetic timelines + EoH + research
-- =========================================

CREATE SCHEMA IF NOT EXISTS ehr;
- `database/sql/18_nice_audit.sql:0-5` → WITH has_chunks_tbl AS (
  SELECT to_regclass('public.rag_corpus_chunks') IS NOT NULL AS exists
),
docs AS (
  SELECT * FROM guidelines.docs WHERE source_key = 'nice'
),
sections AS (
  SELECT s.* FRO
- `frontend/react/src/utils/constants.js:0-5` → export const SYMPTOMS = [
  { value: 'fatigue', label: 'Fatigue' },
  { value: 'joint_pain', label: 'Joint Pain' },
  { value: 'brain_fog', label: 'Brain Fog' },
  { value: 'headache', label: 'Headach
- `server/api/eoh_gap_retrieval.py:0-5` → # server/api/eoh_gap_retrieval.py

from __future__ import annotations

import json
import logging
from typing import Any, Dict, List

logger = logging.getLogger(__name__)

EOH_GAP_RETRIEVAL_SYSTEM_PRO
- `nlp_engines/unified_engine.py:0-5` → from typing import List, Dict, Any, Optional
from abc import ABC, abstractmethod
import logging

logger = logging.getLogger(__name__)

class UnifiedQueryEngine(ABC):
    """Unified interface for vecto
- `frontend/react/src/components/layout/Navbar.css:0-5` → .navbar {
  background-color: white;
  height: 80px;
  display: flex;
  justify-content: center;
  align-items: center;
  position: sticky;
  top: 0;
  z-index: 999;
  box-shadow: 0 2px 10px rgba(0, 0
- `frontend/react/src/components/journal/JournalAnalysisDisplay.js:0-5` → import React from 'react';
import { parseJournalAnalysis } from '../../utils/parseJournalAnalysis';
import DiagnosisTable from './DiagnosisTable';
import DebugBlock from '../common/DebugBlock';
import
- `database/sql/chv_best.sql:0-5` → BEGIN;
CREATE SCHEMA IF NOT EXISTS ontology;

-- Drop whatever "chv_best" currently is (table, view, or matview) without aborting
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM pg_class c JOIN pg_namespa
- `database/sql/integrity_report.sql:0-5` → -- Human-readable integrity snapshot (one result set)
WITH m AS (
  SELECT 'db'::text section, 'size_pretty'::text metric,
         pg_size_pretty(pg_database_size(current_database()))::text AS value,
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
- `server/eoh/module_49b_policy.py:0-5` → # server/eoh/module_49b_policy.py
#
# Module 49B — Diagnostic Consistency Sentinel
#
# This encodes the weight and threshold policies described in Appendix F.49B.
# It is deliberately "thin": a govern
- `./fmp/agents/global_triage_agent.py:0-5` → - CODER: keywords {"implement", "feature", "task", "build", "add", "code"}
- `./fmp/agents/global_triage_agent.py:0-5` → coder_keys = {"implement", "feature", "task", "build", "add", "code"}
