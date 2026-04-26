🚀 Starting MKG retrieval harness
📚 Reading questions file: server/scripts/mkg_retrieval_questions_10.txt
❓ Loaded 10 question(s)
📚 Batch mode enabled
➡️ Batch question 1/10: First-line therapy for T2DM with CKD considerations
🧰 No --sources filter; searching full pilot slice
📚 Loaded pilot source dictionary (38 keys)
🧭 Running source-router stage with eoh-llama3.2-source-router
🧭 Source-router model=eoh-llama3.2-source-router num_ctx=8192
🧭 Router done qtype=D ts_terms=4 sources=3
🧰 Router-restricted sources active (3)
✍️ Embedding router-rewritten semantic query
🧠 Loading embedding model=BAAI/bge-base-en-v1.5 on device=cuda
Warning: You are sending unauthenticated requests to the HF Hub. Please set a HF_TOKEN to enable higher rate limits and faster downloads.
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights:  66%|██████▋   | 132/199 [00:00<00:00, 1307.66it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 1823.76it/s]
📐 Embedding query (183 chars)
✅ Query embedding complete in 51.1953s
🔐 Using database URL from SYNC_DATABASE_URL
🗄️ Running semantic + TS retrieval (top_k=8)
📊 DB done in 0.1980s (semantic=8 ts=8 via per_term (4 terms))
🔀 Overlap computed (both=0 jaccard=0.000)
🧪 Running Ollama synthesis pass model=eoh-llama:70b
🧾 Preparing retrieval bundle for LLM analysis
🤖 Calling Ollama model=eoh-llama:70b num_ctx=32768 timeout=180s
⚠️ LLM synthesis failed: 500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat
➡️ Batch question 2/10: When should SGLT2 inhibitors be started in CKD with diabetes?
🧰 No --sources filter; searching full pilot slice
📚 Loaded pilot source dictionary (38 keys)
🧭 Running source-router stage with eoh-llama3.2-source-router
🧭 Source-router model=eoh-llama3.2-source-router num_ctx=8192
🧭 Router done qtype=D ts_terms=3 sources=3
🧰 Router-restricted sources active (3)
✍️ Embedding router-rewritten semantic query
🧠 Loading embedding model=BAAI/bge-base-en-v1.5 on device=cuda
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 2411.08it/s]
📐 Embedding query (537 chars)
✅ Query embedding complete in 2.4071s
🔐 Using database URL from SYNC_DATABASE_URL
🗄️ Running semantic + TS retrieval (top_k=8)
🔁 Per-term TS empty/thin; merging raw-query fallback
📊 DB done in 0.0396s (semantic=8 ts=8 via per_term+raw_fallback (3 terms))
🔀 Overlap computed (both=2 jaccard=0.143)
🧪 Running Ollama synthesis pass model=eoh-llama:70b
🧾 Preparing retrieval bundle for LLM analysis
🤖 Calling Ollama model=eoh-llama:70b num_ctx=32768 timeout=180s
⚠️ LLM synthesis failed: 500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat
➡️ Batch question 3/10: Which agents reduce renal outcomes in diabetic kidney disease?
🧰 No --sources filter; searching full pilot slice
📚 Loaded pilot source dictionary (38 keys)
🧭 Running source-router stage with eoh-llama3.2-source-router
🧭 Source-router model=eoh-llama3.2-source-router num_ctx=8192
🧭 Router done qtype=D ts_terms=4 sources=3
🧰 Router-restricted sources active (3)
✍️ Embedding router-rewritten semantic query
🧠 Loading embedding model=BAAI/bge-base-en-v1.5 on device=cuda
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 2398.29it/s]
📐 Embedding query (606 chars)
✅ Query embedding complete in 2.2776s
🔐 Using database URL from SYNC_DATABASE_URL
🗄️ Running semantic + TS retrieval (top_k=8)
📊 DB done in 0.0351s (semantic=8 ts=8 via per_term (4 terms))
🔀 Overlap computed (both=0 jaccard=0.000)
🧪 Running Ollama synthesis pass model=eoh-llama:70b
🧾 Preparing retrieval bundle for LLM analysis
🤖 Calling Ollama model=eoh-llama:70b num_ctx=32768 timeout=180s
⚠️ LLM synthesis failed: 500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat
➡️ Batch question 4/10: How is anemia in chronic kidney disease managed per KDIGO?
🧰 No --sources filter; searching full pilot slice
📚 Loaded pilot source dictionary (38 keys)
🧭 Running source-router stage with eoh-llama3.2-source-router
🧭 Source-router model=eoh-llama3.2-source-router num_ctx=8192
🧭 Router done qtype=OTHER ts_terms=4 sources=3
🧰 Router-restricted sources active (3)
✍️ Embedding router-rewritten semantic query
🧠 Loading embedding model=BAAI/bge-base-en-v1.5 on device=cuda
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 2468.68it/s]
📐 Embedding query (399 chars)
✅ Query embedding complete in 2.2909s
🔐 Using database URL from SYNC_DATABASE_URL
🗄️ Running semantic + TS retrieval (top_k=8)
📊 DB done in 0.0493s (semantic=8 ts=8 via per_term (4 terms))
🔀 Overlap computed (both=0 jaccard=0.000)
🧪 Running Ollama synthesis pass model=eoh-llama:70b
🧾 Preparing retrieval bundle for LLM analysis
🤖 Calling Ollama model=eoh-llama:70b num_ctx=32768 timeout=180s
⚠️ LLM synthesis failed: 500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat
➡️ Batch question 5/10: What are GOLD 2024 escalation steps for COPD maintenance therapy?
🧰 No --sources filter; searching full pilot slice
📚 Loaded pilot source dictionary (38 keys)
🧭 Running source-router stage with eoh-llama3.2-source-router
🧭 Source-router model=eoh-llama3.2-source-router num_ctx=8192
🧭 Router done qtype=D ts_terms=4 sources=3
🧰 Router-restricted sources active (3)
✍️ Embedding router-rewritten semantic query
🧠 Loading embedding model=BAAI/bge-base-en-v1.5 on device=cuda
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 2411.94it/s]
📐 Embedding query (366 chars)
✅ Query embedding complete in 2.3629s
🔐 Using database URL from SYNC_DATABASE_URL
🗄️ Running semantic + TS retrieval (top_k=8)
📊 DB done in 0.0633s (semantic=8 ts=8 via per_term (4 terms))
🔀 Overlap computed (both=2 jaccard=0.143)
🧪 Running Ollama synthesis pass model=eoh-llama:70b
🧾 Preparing retrieval bundle for LLM analysis
🤖 Calling Ollama model=eoh-llama:70b num_ctx=32768 timeout=180s
⚠️ LLM synthesis failed: 500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat
➡️ Batch question 6/10: What does GINA 2023 suggest for step-up asthma control?
🧰 No --sources filter; searching full pilot slice
📚 Loaded pilot source dictionary (38 keys)
🧭 Running source-router stage with eoh-llama3.2-source-router
🧭 Source-router model=eoh-llama3.2-source-router num_ctx=8192
🧭 Router done qtype=OTHER ts_terms=4 sources=3
🧰 Router-restricted sources active (3)
✍️ Embedding router-rewritten semantic query
🧠 Loading embedding model=BAAI/bge-base-en-v1.5 on device=cuda
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 4579.34it/s]
📐 Embedding query (254 chars)
✅ Query embedding complete in 2.3814s
🔐 Using database URL from SYNC_DATABASE_URL
🗄️ Running semantic + TS retrieval (top_k=8)
📊 DB done in 0.0521s (semantic=8 ts=8 via per_term (4 terms))
🔀 Overlap computed (both=1 jaccard=0.067)
🧪 Running Ollama synthesis pass model=eoh-llama:70b
🧾 Preparing retrieval bundle for LLM analysis
🤖 Calling Ollama model=eoh-llama:70b num_ctx=32768 timeout=180s
⚠️ LLM synthesis failed: 500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat
➡️ Batch question 7/10: How do ADA 2024 recommendations prioritize GLP-1 vs SGLT2 in CKD?
🧰 No --sources filter; searching full pilot slice
📚 Loaded pilot source dictionary (38 keys)
🧭 Running source-router stage with eoh-llama3.2-source-router
🧭 Source-router model=eoh-llama3.2-source-router num_ctx=8192
🧭 Router done qtype=OTHER ts_terms=3 sources=2
🧰 Router-restricted sources active (2)
✍️ Embedding router-rewritten semantic query
🧠 Loading embedding model=BAAI/bge-base-en-v1.5 on device=cuda
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 2446.41it/s]
📐 Embedding query (379 chars)
✅ Query embedding complete in 2.2067s
🔐 Using database URL from SYNC_DATABASE_URL
🗄️ Running semantic + TS retrieval (top_k=8)
🔁 Per-term TS empty/thin; merging raw-query fallback
🔤 TS tier-1 miss; extracting key terms for OR-expansion
📊 DB done in 0.0505s (semantic=8 ts=8 via per_term+raw_fallback (3 terms))
🔀 Overlap computed (both=0 jaccard=0.000)
🧪 Running Ollama synthesis pass model=eoh-llama:70b
🧾 Preparing retrieval bundle for LLM analysis
🤖 Calling Ollama model=eoh-llama:70b num_ctx=32768 timeout=180s
⚠️ LLM synthesis failed: 500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat
➡️ Batch question 8/10: Key treatment principles for lupus nephritis in EULAR/KDIGO guidance
🧰 No --sources filter; searching full pilot slice
📚 Loaded pilot source dictionary (38 keys)
🧭 Running source-router stage with eoh-llama3.2-source-router
🧭 Source-router model=eoh-llama3.2-source-router num_ctx=8192
🧭 Router done qtype=OTHER ts_terms=7 sources=3
🧰 Router-restricted sources active (3)
✍️ Embedding router-rewritten semantic query
🧠 Loading embedding model=BAAI/bge-base-en-v1.5 on device=cuda
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 2539.35it/s]
📐 Embedding query (344 chars)
✅ Query embedding complete in 2.1839s
🔐 Using database URL from SYNC_DATABASE_URL
🗄️ Running semantic + TS retrieval (top_k=8)
📊 DB done in 0.0373s (semantic=8 ts=8 via per_term (7 terms))
🔀 Overlap computed (both=2 jaccard=0.143)
🧪 Running Ollama synthesis pass model=eoh-llama:70b
🧾 Preparing retrieval bundle for LLM analysis
🤖 Calling Ollama model=eoh-llama:70b num_ctx=32768 timeout=180s
⚠️ LLM synthesis failed: 500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat
➡️ Batch question 9/10: When are nonsteroidal MRAs considered in CKD and diabetes?
🧰 No --sources filter; searching full pilot slice
📚 Loaded pilot source dictionary (38 keys)
🧭 Running source-router stage with eoh-llama3.2-source-router
🧭 Source-router model=eoh-llama3.2-source-router num_ctx=8192
🧭 Router done qtype=D ts_terms=4 sources=3
🧰 Router-restricted sources active (3)
✍️ Embedding router-rewritten semantic query
🧠 Loading embedding model=BAAI/bge-base-en-v1.5 on device=cuda
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 2459.54it/s]
📐 Embedding query (462 chars)
✅ Query embedding complete in 2.2176s
🔐 Using database URL from SYNC_DATABASE_URL
🗄️ Running semantic + TS retrieval (top_k=8)
📊 DB done in 0.0364s (semantic=8 ts=8 via per_term (4 terms))
🔀 Overlap computed (both=1 jaccard=0.067)
🧪 Running Ollama synthesis pass model=eoh-llama:70b
🧾 Preparing retrieval bundle for LLM analysis
🤖 Calling Ollama model=eoh-llama:70b num_ctx=32768 timeout=180s
⚠️ LLM synthesis failed: 500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat
➡️ Batch question 10/10: Summarize opioid prescribing cautions from CDC guidance
🧰 No --sources filter; searching full pilot slice
📚 Loaded pilot source dictionary (38 keys)
🧭 Running source-router stage with eoh-llama3.2-source-router
🧭 Source-router model=eoh-llama3.2-source-router num_ctx=8192
🧭 Router done qtype=C ts_terms=5 sources=3
🧰 Router-restricted sources active (3)
✍️ Embedding router-rewritten semantic query
🧠 Loading embedding model=BAAI/bge-base-en-v1.5 on device=cuda
Loading weights:   0%|          | 0/199 [00:00<?, ?it/s]Loading weights: 100%|██████████| 199/199 [00:00<00:00, 2447.09it/s]
📐 Embedding query (348 chars)
✅ Query embedding complete in 2.1729s
🔐 Using database URL from SYNC_DATABASE_URL
🗄️ Running semantic + TS retrieval (top_k=8)
📊 DB done in 0.0430s (semantic=8 ts=8 via per_term (5 terms))
🔀 Overlap computed (both=0 jaccard=0.000)
🧪 Running Ollama synthesis pass model=eoh-llama:70b
🧾 Preparing retrieval bundle for LLM analysis
🤖 Calling Ollama model=eoh-llama:70b num_ctx=32768 timeout=180s
⚠️ LLM synthesis failed: 500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat
📦 Emitting batch JSON output (201218 chars)
{
  "batch": {
    "n_questions": 10,
    "elapsed_sec": 122.852,
    "model": "eoh-llama",
    "synth_model": "eoh-llama:70b",
    "router_model": "eoh-llama3.2-source-router",
    "use_router": true,
    "router_restrict_sources": true,
    "embed_model": "BAAI/bge-base-en-v1.5"
  },
  "runs": [
    {
      "query": "First-line therapy for T2DM with CKD considerations",
      "top_k": 8,
      "sources_filter": null,
      "embed_model": "BAAI/bge-base-en-v1.5",
      "pilot_slice_source_reference": {
        "rxnorm": "NLM RxNorm drug and ingredient concepts (RxCUI, names, TTYs).",
        "loinc": "LOINC laboratory and clinical observation codes with long names.",
        "hpo": "Human Phenotype Ontology terms (phenotypes, disease manifestations).",
        "snomed": "SNOMED CT clinical concepts (disorders, findings, procedures).",
        "icd10cm": "ICD-10-CM diagnosis codes and official long titles (US clinical modification).",
        "icd11": "WHO ICD-11 foundation mortality and morbidity content mirrored for search.",
        "orphanet": "Orphanet rare disease names, synonyms, and classification text.",
        "chv": "Consumer Health Vocabulary \u2014 lay-language terms linked to clinical concepts (UMLS CHV).",
        "va_guidelines": "VA/DoD clinical practice guideline sections ingested as rag_corpus chunks.",
        "acc_aha_valvular_2020": "2020 ACC/AHA guideline on valvular heart disease (chunked text).",
        "ada_dm_2024": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage).",
        "kdigo_ckd_2021": "KDIGO 2021 clinical practice guideline for chronic kidney disease (CKD).",
        "kdigo_ckd_2024": "KDIGO 2024 CKD evaluation and management guideline excerpts.",
        "kdigo_gn_ln_2021": "KDIGO 2021 guideline for glomerular diseases including lupus nephritis.",
        "kdigo_anemia_ckd_2023": "KDIGO 2023 clinical practice guideline for anemia in CKD.",
        "gold_copd_2023": "GOLD 2023 Global Strategy for Diagnosis, Management, and Prevention of COPD.",
        "gold_copd_2024": "GOLD 2024 COPD strategy document excerpts.",
        "gina_asthma_2023": "GINA 2023 Global Strategy for Asthma Management and Prevention.",
        "cdc_opioid": "CDC opioid prescribing guideline narrative sections (structured plain text).",
        "acr_eular": "Joint ACR/EULAR classification or criteria publications (combined tag).",
        "acr_ild_2023": "ACR guidance on idiopathic inflammatory myopathies with ILD (2023).",
        "acr_ra_2021": "ACR guideline or guidance on rheumatoid arthritis management (2021).",
        "acr_npf_psa_2018": "ACR/NPF joint guideline on psoriasis and psoriatic arthritis (2018).",
        "acr_vf_anca_2021": "ACR/VF guideline on ANCA-associated vasculitis (2021).",
        "acr_reproductive_health_2020": "ACR reproductive health guidance for rheumatic disease (2020).",
        "eular_acr_sle_2019": "EULAR/ACR classification criteria or lupus management collaboration (2019).",
        "eular_ra_2022": "EULAR recommendations for rheumatoid arthritis management (2022).",
        "eular_psa_2020": "EULAR recommendations for psoriatic arthritis pharmacologic therapy (2020).",
        "eular_sle_nephritis_2025": "EULAR recommendations on management of lupus nephritis (2025).",
        "eular_anca_2022": "EULAR recommendations for ANCA-associated vasculitis (2022).",
        "eular_lvv_2018": "EULAR recommendations for large-vessel vasculitis (2018).",
        "eular_axspa_2022": "EULAR recommendations for axial spondyloarthritis (2022).",
        "asas_eular_axspa_2022": "ASAS\u2013EULAR recommendations for axial spondyloarthritis (2022).",
        "diagrules": "Curated diagnostic-rule narrative cards used as RAG chunks.",
        "eoh_canon_v6": "Ethos of Health canon v6 narrative chunks (foundational clinical ethos text).",
        "eoh_2025": "Ethos of Health 2025 corpus excerpts in rag_corpus.",
        "eoh_gold_2025": "Ethos of Health \u00d7 GOLD COPD 2025 cross-reference or summary chunks.",
        "ethos_model": "Short Ethos-of-Health model or meta documents (small row count)."
      },
      "router_plan": {
        "question_type": "D",
        "semantic_query": "First-line therapy for T2DM with CKD considerations. What are the most effective treatments and management plans for patients with type 2 diabetes mellitus and chronic kidney disease?",
        "ts_query": "(T2DM AND CKD) OR (diabetes AND kidney disease)",
        "ts_terms": [
          "T2DM",
          "CKD",
          "type 2 diabetes mellitus",
          "chronic kidney disease"
        ],
        "selected_sources": [
          {
            "source": "kdigo_ckd_2021",
            "priority": 1,
            "why": "KDIGO 2021 clinical practice guideline for chronic kidney disease"
          },
          {
            "source": "ada_dm_2024",
            "priority": 2,
            "why": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage)"
          },
          {
            "source": "cdc_opioid",
            "priority": 3,
            "why": "CDC opioid prescribing guideline narrative sections"
          }
        ],
        "selected_modules": [
          {
            "module_id": "M13",
            "priority": 1,
            "why": "Trend & Prognostic Engine"
          },
          {
            "module_id": "M6",
            "priority": 2,
            "why": "Escalation Router / Central Switchboard"
          },
          {
            "module_id": "M12",
            "priority": 3,
            "why": "Symptom Narrative Engine"
          }
        ],
        "notes": "First-line therapy for T2DM with CKD considerations",
        "elapsed_sec": 5.879,
        "model": "eoh-llama3.2-source-router"
      },
      "effective_sources": [
        "kdigo_ckd_2021",
        "ada_dm_2024",
        "cdc_opioid"
      ],
      "embed_device": "cuda",
      "embed_text": "First-line therapy for T2DM with CKD considerations. What are the most effective treatments and management plans for patients with type 2 diabetes mellitus and chronic kidney disease?",
      "embed_sec": 51.1953,
      "db_sec": 0.198,
      "ts_strategy": "per_term (4 terms)",
      "ts_terms_used": [
        "T2DM",
        "CKD",
        "type 2 diabetes mellitus",
        "chronic kidney disease"
      ],
      "semantic_hits": [
        {
          "id": 11244308,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0200",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 200",
          "text": "leading to the recommendation that sem-\na g l u t i d ec a nb eu s e da sa n o t h e r\ufb01rst-line\nagent for people with CKD (137,138).\nOther GLP-1 RAs (liraglutide and dulaglu-\ntide) may also have CKD bene\ufb01ts, but no\nother dedicated kidney trials have been\npublished. Similarly, no dedicated kidney\noutcomes studies for the dual GIP and\nGLP-1 RA (tirzepatide) have been pub-\nlished. Dedicated kidney outcomes trials\nin people with CKD and type 2 diabetes\nhave shown that\u2026[truncated]",
          "score": 0.7701326012611389
        },
        {
          "id": 11246262,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0102",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 102",
          "text": "appears to be irrespective of the level of GFR, with no\nevidence of a threshold level of eGFR below which ben-\ne\ufb01ts start to attenuate.\nFor the 1A recommendation (3.7.1), also see the 2022\nupdate to the KDIGO Clinical Practice Guideline in Diabetes\nManagement for details of the certainty of the evidence.\n23 Our\nERT speci\ufb01cally also undertook a systematic review limited to\npeople with CKD and no diabetes and considered the\ncertainty of the effect in this subgroup t\u2026[truncated]",
          "score": 0.7694556850519382
        },
        {
          "id": 11244318,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0210",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 210",
          "text": "diabetes: a meta-analysis. JAMA Cardiol 2021;6:\n148\u2013158\n140. Reyes-Farias CI, Reategui-Diaz M, Romani-\nRomani F, Prokop L. The effect of sodium-glucose\ncotransporter 2 inhibitors in patients with chronic\nkidney disease with or without type 2 diabetes\nmellitus on cardiovascular and renal outcomes: a\nsystematic review and meta-analysis. PLoS One\n2023;18:e0295059\n141. Herrington WG, Staplin N, Wanner C, et al.;\nEmpa-Kidney Collaborative Group. Empagli\ufb02ozin\nin patient\u2026[truncated]",
          "score": 0.7676782150460367
        },
        {
          "id": 11244357,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0249",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 249",
          "text": "Comorbidities,\u201d for further information on\nimmunization).\nPrevention\nThe only proven primary prevention inter-\nventions for CKD in people with diabetes\na r eb l o o dg l u c o s e( A 1 Cg o a lo f7 % )a n d\nblood pressure management. There is no\nevidence that renin-angiotensin-aldosterone\nsystem inhibitors or any other interventions\nprevent the development of CKD in the ab-\nsence of hypertension or albuminuria. Thus,\nthe American Diabetes Association does not\nreco\u2026[truncated]",
          "score": 0.7608238458633423
        },
        {
          "id": 11246259,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0099",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 99",
          "text": "eGFR <30 ml/min per 1.73 m2, compared with those who\ncontinue.508,509 In addition, a recent individual patient level\ndata meta-analysis demonstrated a bene\ufb01t in delaying KRT\nin patients with eGFR<30 ml/min per 1.73 m2.510\n3.7 Sodium-glucose cotransporter-2 inhibitors\n(SGLT2i)\nThe Work Group concurs with the KDIGO 2022 Clinical\nPractice Guideline for Diabetes Management in Chronic\nKidney Disease, which stated: \u201cWe recommend treating pa-\ntients with type 2 diabetes \u2026[truncated]",
          "score": 0.7599523210553945
        },
        {
          "id": 11246266,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0106",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 106",
          "text": "Special considerations\nPediatric considerations. No relevant studies to inform this\nguideline have been completed in children.\n3.9 Glucagon-like peptide-1 receptor agonists\n(GLP-1 RA)\nThe Work Group highlights a key recommendation and practice\npoint from the KDIGO 2022 Clinical Practice Guideline for\nDiabetes Management in Chronic Kidney Disease.23\nRecommendation 3.9.1: In adults with T2D and CKD\nwho have not achieved individualized glycemic\ntargets despite use of\u2026[truncated]",
          "score": 0.7558846764702044
        },
        {
          "id": 11246260,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0100",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 100",
          "text": "without diabetes who are at very low risk of ketoacidosis). SGLT2i\nalso favorably reduce BP, uric acid levels, measures of\ufb02uid over-\nload, the risk of serious hyperkalemia, and do not increase risk of\nhypoglycemia. The recommendation is consistent with but ex-\npands on Recommendation 1.3.1 from theKDIGO 2022 Clinical\nPractice Guideline for Diabetes Management in Chronic Kid-\nney Diseaseto include people with causes of CKD not related to\ndiabetes.\nKey information\nB\u2026[truncated]",
          "score": 0.7551831152926032
        },
        {
          "id": 11244124,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0016",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 16",
          "text": "and worsening of cardiometabolic abnor-\nmalities that often result from sudden\ndiscontinuation of weight management\npharmacotherapy.\nRecommendation 8.25 was revised to\nemphasize use of a CGM device to im-\nprove safety in individuals with post\u2013\nmetabolic surgery hypoglycemia.\nUpdated Tables 8.1 and 8.2 provide\ndetailed information on the ef\ufb01cacy, com-\nmon side effects, safety considerations,\nand costs of approved weight manage-\nment pharmacotherapy options.\nDiscuss\u2026[truncated]",
          "score": 0.7549792236064993
        }
      ],
      "ts_hits": [
        {
          "id": 11244418,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0310",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 310",
          "text": "relationship to type 2 diabetes mellitus. J Pediatr\nEndocrinol Metab 2002;15(Suppl 1):509\u2013517\n179. Naughton MJ. Health-related quality of life\nof children and adolescents with type 1 or type 2\ndiabetes mellitus: SEARCH for Diabetes in Youth\nStudy. Arch Pediatr Adolesc Med 2008;162:\n649\u2013657\n180. Wadden TA, Webb VL, Moran CH, Bailer BA.\nLifestyle modi\ufb01cation for obesity: new dev-\nelopments in diet, physical activity, and behavior\ntherapy. Circulation 2012;125:1157\u20131\u2026[truncated]",
          "score": 0.9999997
        },
        {
          "id": 11244317,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0209",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 209",
          "text": "99. Salpeter SR, Greyber E, Pasternak GA,\nSalpeter EE. Risk of fatal and nonfatal lactic\nacidosis with metformin use in type 2 diabetes\nmellitus: systematic review and meta-analysis.\nArch Intern Med 2003;163:2594\u20132602\n100. Salpeter SR, Greyber E, Pasternak GA,\nSalpeter EE. Risk of fatal and nonfatal lactic\nacidosis with metformin use in type 2 diabetes\nmellitus. Cochrane Database Syst Rev 2010;2010:\nCD002967\n101. Lipska KJ, Bailey CJ, Inzucchi SE. Use of\nmetformin\u2026[truncated]",
          "score": 0.9999979
        },
        {
          "id": 11244256,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0148",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 148",
          "text": "33. Salabelle C, Ly Sall K, Eroukhmanoff J, et al.\nCOVID-19 pandemic lockdown in young people\nwith type 1 diabetes: positive results of an\nunprecedented challenge for patients through\ntelemedicine and change in use of continuous\nglucose monitoring. Prim Care Diabetes 2021;\n15:884\u2013886\n34. Prabhu Navis J, Leelarathna L, Mubita W,\net al. Impact of COVID-19 lockdown on\ufb02ash and\nreal-time glucose sensor users with type 1\ndiabetes in England. Acta Diabetol 2021;58:\n231\u20132\u2026[truncated]",
          "score": 0.9999953
        },
        {
          "id": 11246340,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0180",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 180",
          "text": "References\n1. Kidney Disease: Improving Global Outcomes CKD Work Group. KDIGO\n2012 clinical practice guideline for the evaluation and management of\nchronic kidney disease.Kidney Int Suppl. 2012;3:S1\u2013S150.\n2. National Kidney Foundation. K/DOQI clinical practice guidelines for\nchronic kidney disease: evaluation, classi\ufb01cation, and strati\ufb01cation. Am\nJ Kidney Dis. 2002;39(suppl 1):S1\u2013S266.\n3. Levey AS, de Jong PE, Coresh J, et al. The de\ufb01nition, classi\ufb01cation, and\npro\u2026[truncated]",
          "score": 0.9999939
        },
        {
          "id": 11246348,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0188",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 188",
          "text": "392. Lambers Heerspink HJ, Gansevoort RT. Albuminuria is an appropriate\ntherapeutic target in patients with CKD: the pro view. Clin J Am Soc\nNephrol. 2015;10:1079\u20131088.\n393. Fuhrman DY, Schneider MF, Dell KM, et al. Albuminuria, proteinuria, and\nrenal disease progression in children with CKD.Clin J Am Soc Nephrol.\n2017;12:912\u2013920.\n394. Harambat J, Kunzmann K, Azukaitis K, et al. Metabolic acidosis is\ncommon and associates with disease progression in children with\n\u2026[truncated]",
          "score": 0.9999268
        },
        {
          "id": 11246358,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0198",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 198",
          "text": "858. Lu PH, Chung CH, Chuo HE, et al. Ef\ufb01cacy of acupoint stimulation as a\ntreatment for uremic pruritus: a systematic review and meta-analysis.\nFront Med (Lausanne). 2022;9:1036072.\n859. Simonsen E, Komenda P, Lerner B, et al. Treatment of uremic pruritus: a\nsystematic review. Am J Kidney Dis. 2017;70:638\u2013655.\n860. Mettang T, Kremer AE. Uremic pruritus.Kidney Int. 2015;87:685\u2013691.\n861. Manenti L, Tansinda P, Vaglio A. Uraemic pruritus: clinical characteristics,\np\u2026[truncated]",
          "score": 0.99948287
        },
        {
          "id": 11246215,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0055",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 55",
          "text": "and transplantation).56 A public health approach toward CKD\ndetection and treatment could reduce inequities in the burden\nof kidney failure by slowing the rate of progression and the\nrisk of CVD for everyone.\n57\nThe possible harm of early detection of CKD is that the\nnew diagnosis may cause anxiety in some people, particularly\nif the testing is not discussed in advance of the results. Dis-\ncussions around disease detection are common in the primary\ncare setting, a\u2026[truncated]",
          "score": 0.098602496
        },
        {
          "id": 11246250,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0090",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 90",
          "text": "Chapter 3: Delaying CKD progression and managing\nits complications\n3.1 CKD treatment and risk modi\ufb01cation\nPractice Point 3.1.1: Treat people with CKD with a\ncomprehensive treatment strategy to reduce risks of\nprogression of CKD and its associated complications\n(Figure 17).\nRisk factors associated with CKD progression, CVD, and\nother CKD complications are highly interrelated,\n435 and\nhence so is their management. We use the term \u201cCKD\ntreatment and risk modi\ufb01cation\u201d\u2026[truncated]",
          "score": 0.098287635
        }
      ],
      "overlap": {
        "semantic_only": [
          11244124,
          11244308,
          11244318,
          11244357,
          11246259,
          11246260,
          11246262,
          11246266
        ],
        "ts_only": [
          11244256,
          11244317,
          11244418,
          11246215,
          11246250,
          11246340,
          11246348,
          11246358
        ],
        "both": [],
        "jaccard": 0.0
      },
      "llm": {
        "error": "500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat",
        "model": "eoh-llama:70b"
      },
      "batch_index": 1
    },
    {
      "query": "When should SGLT2 inhibitors be started in CKD with diabetes?",
      "top_k": 8,
      "sources_filter": null,
      "embed_model": "BAAI/bge-base-en-v1.5",
      "pilot_slice_source_reference": {
        "rxnorm": "NLM RxNorm drug and ingredient concepts (RxCUI, names, TTYs).",
        "loinc": "LOINC laboratory and clinical observation codes with long names.",
        "hpo": "Human Phenotype Ontology terms (phenotypes, disease manifestations).",
        "snomed": "SNOMED CT clinical concepts (disorders, findings, procedures).",
        "icd10cm": "ICD-10-CM diagnosis codes and official long titles (US clinical modification).",
        "icd11": "WHO ICD-11 foundation mortality and morbidity content mirrored for search.",
        "orphanet": "Orphanet rare disease names, synonyms, and classification text.",
        "chv": "Consumer Health Vocabulary \u2014 lay-language terms linked to clinical concepts (UMLS CHV).",
        "va_guidelines": "VA/DoD clinical practice guideline sections ingested as rag_corpus chunks.",
        "acc_aha_valvular_2020": "2020 ACC/AHA guideline on valvular heart disease (chunked text).",
        "ada_dm_2024": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage).",
        "kdigo_ckd_2021": "KDIGO 2021 clinical practice guideline for chronic kidney disease (CKD).",
        "kdigo_ckd_2024": "KDIGO 2024 CKD evaluation and management guideline excerpts.",
        "kdigo_gn_ln_2021": "KDIGO 2021 guideline for glomerular diseases including lupus nephritis.",
        "kdigo_anemia_ckd_2023": "KDIGO 2023 clinical practice guideline for anemia in CKD.",
        "gold_copd_2023": "GOLD 2023 Global Strategy for Diagnosis, Management, and Prevention of COPD.",
        "gold_copd_2024": "GOLD 2024 COPD strategy document excerpts.",
        "gina_asthma_2023": "GINA 2023 Global Strategy for Asthma Management and Prevention.",
        "cdc_opioid": "CDC opioid prescribing guideline narrative sections (structured plain text).",
        "acr_eular": "Joint ACR/EULAR classification or criteria publications (combined tag).",
        "acr_ild_2023": "ACR guidance on idiopathic inflammatory myopathies with ILD (2023).",
        "acr_ra_2021": "ACR guideline or guidance on rheumatoid arthritis management (2021).",
        "acr_npf_psa_2018": "ACR/NPF joint guideline on psoriasis and psoriatic arthritis (2018).",
        "acr_vf_anca_2021": "ACR/VF guideline on ANCA-associated vasculitis (2021).",
        "acr_reproductive_health_2020": "ACR reproductive health guidance for rheumatic disease (2020).",
        "eular_acr_sle_2019": "EULAR/ACR classification criteria or lupus management collaboration (2019).",
        "eular_ra_2022": "EULAR recommendations for rheumatoid arthritis management (2022).",
        "eular_psa_2020": "EULAR recommendations for psoriatic arthritis pharmacologic therapy (2020).",
        "eular_sle_nephritis_2025": "EULAR recommendations on management of lupus nephritis (2025).",
        "eular_anca_2022": "EULAR recommendations for ANCA-associated vasculitis (2022).",
        "eular_lvv_2018": "EULAR recommendations for large-vessel vasculitis (2018).",
        "eular_axspa_2022": "EULAR recommendations for axial spondyloarthritis (2022).",
        "asas_eular_axspa_2022": "ASAS\u2013EULAR recommendations for axial spondyloarthritis (2022).",
        "diagrules": "Curated diagnostic-rule narrative cards used as RAG chunks.",
        "eoh_canon_v6": "Ethos of Health canon v6 narrative chunks (foundational clinical ethos text).",
        "eoh_2025": "Ethos of Health 2025 corpus excerpts in rag_corpus.",
        "eoh_gold_2025": "Ethos of Health \u00d7 GOLD COPD 2025 cross-reference or summary chunks.",
        "ethos_model": "Short Ethos-of-Health model or meta documents (small row count)."
      },
      "router_plan": {
        "question_type": "D",
        "semantic_query": "When should SGLT2 inhibitors be started in CKD with diabetes? This question pertains to the initiation of therapy for patients with chronic kidney disease (CKD) and diabetes, focusing on the use of sodium-glucose cotransporter 2 (SGLT2) inhibitors. These medications are a class of oral hypoglycemic agents that have been shown to slow the progression of kidney disease in patients with CKD and type 2 diabetes. The question seeks guidance on when SGLT2 inhibitors should be initiated as part of the treatment regimen for these patients.",
        "ts_query": "(SGLT2 inhibitor OR \"sodium-glucose cotransporter 2 inhibitor\") AND (CKD OR chronic kidney disease) AND (diabetes OR type 2 diabetes)",
        "ts_terms": [
          "SGLT2",
          "CKD",
          "diabetes"
        ],
        "selected_sources": [
          {
            "source": "ada_dm_2024",
            "priority": 1,
            "why": "American Diabetes Association Standards of Care provides guidance on the use of SGLT2 inhibitors in patients with CKD and diabetes."
          },
          {
            "source": "kdigo_ckd_2021",
            "priority": 2,
            "why": "KDIGO 2021 clinical practice guideline for chronic kidney disease includes recommendations for the use of SGLT2 inhibitors in patients with CKD and type 2 diabetes."
          },
          {
            "source": "cdc_opioid",
            "priority": 3,
            "why": "CDC opioid prescribing guideline narrative sections provide information on the use of SGLT2 inhibitors as part of a comprehensive treatment plan for patients with CKD and diabetes."
          }
        ],
        "selected_modules": [
          {
            "module_id": "M13",
            "priority": 1,
            "why": "Trend & Prognostic Engine can help answer questions about flare risk over time and trajectory improvement/worsening."
          },
          {
            "module_id": "M14",
            "priority": 2,
            "why": "Action & Escalation Engine can provide guidance on concrete next steps for patients with CKD and diabetes."
          }
        ],
        "notes": "This routing plan prioritizes sources that provide clinical guidelines and recommendations for the use of SGLT2 inhibitors in patients with CKD and diabetes.",
        "elapsed_sec": 4.056,
        "model": "eoh-llama3.2-source-router"
      },
      "effective_sources": [
        "ada_dm_2024",
        "kdigo_ckd_2021",
        "cdc_opioid"
      ],
      "embed_device": "cuda",
      "embed_text": "When should SGLT2 inhibitors be started in CKD with diabetes? This question pertains to the initiation of therapy for patients with chronic kidney disease (CKD) and diabetes, focusing on the use of sodium-glucose cotransporter 2 (SGLT2) inhibitors. These medications are a class of oral hypoglycemic agents that have been shown to slow the progression of kidney disease in patients with CKD and type 2 diabetes. The question seeks guidance on when SGLT2 inhibitors should be initiated as part of the treatment regimen for these patients.",
      "embed_sec": 2.4071,
      "db_sec": 0.0396,
      "ts_strategy": "per_term+raw_fallback (3 terms)",
      "ts_terms_used": [
        "SGLT2",
        "CKD",
        "diabetes"
      ],
      "semantic_hits": [
        {
          "id": 11244308,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0200",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 200",
          "text": "leading to the recommendation that sem-\na g l u t i d ec a nb eu s e da sa n o t h e r\ufb01rst-line\nagent for people with CKD (137,138).\nOther GLP-1 RAs (liraglutide and dulaglu-\ntide) may also have CKD bene\ufb01ts, but no\nother dedicated kidney trials have been\npublished. Similarly, no dedicated kidney\noutcomes studies for the dual GIP and\nGLP-1 RA (tirzepatide) have been pub-\nlished. Dedicated kidney outcomes trials\nin people with CKD and type 2 diabetes\nhave shown that\u2026[truncated]",
          "score": 0.7981481792750201
        },
        {
          "id": 11246259,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0099",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 99",
          "text": "eGFR <30 ml/min per 1.73 m2, compared with those who\ncontinue.508,509 In addition, a recent individual patient level\ndata meta-analysis demonstrated a bene\ufb01t in delaying KRT\nin patients with eGFR<30 ml/min per 1.73 m2.510\n3.7 Sodium-glucose cotransporter-2 inhibitors\n(SGLT2i)\nThe Work Group concurs with the KDIGO 2022 Clinical\nPractice Guideline for Diabetes Management in Chronic\nKidney Disease, which stated: \u201cWe recommend treating pa-\ntients with type 2 diabetes \u2026[truncated]",
          "score": 0.7965601450395339
        },
        {
          "id": 11246260,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0100",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 100",
          "text": "without diabetes who are at very low risk of ketoacidosis). SGLT2i\nalso favorably reduce BP, uric acid levels, measures of\ufb02uid over-\nload, the risk of serious hyperkalemia, and do not increase risk of\nhypoglycemia. The recommendation is consistent with but ex-\npands on Recommendation 1.3.1 from theKDIGO 2022 Clinical\nPractice Guideline for Diabetes Management in Chronic Kid-\nney Diseaseto include people with causes of CKD not related to\ndiabetes.\nKey information\nB\u2026[truncated]",
          "score": 0.7884624978669006
        },
        {
          "id": 11244359,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0251",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 251",
          "text": "activity (92\u201394). Glucagon-like peptide 1\n(GLP-1) receptor agonists (RAs) have\nalso been shown to improve kidney out-\ncomes (95\u2013100). Kidney effects should\nbe considered when selecting agents\nfor glucose lowering (see Section 9,\n\u201cPharmacologic Approaches to Glycemic\nTreatment\u201d).\nSelection of Glucose-Lowering\nMedications for People With Chronic\nKidney Disease\nFor people with type 2 diabetes and es-\ntablished CKD, special considerations for\nthe selection of glucose-\u2026[truncated]",
          "score": 0.7856188182348536
        },
        {
          "id": 11244318,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0210",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 210",
          "text": "diabetes: a meta-analysis. JAMA Cardiol 2021;6:\n148\u2013158\n140. Reyes-Farias CI, Reategui-Diaz M, Romani-\nRomani F, Prokop L. The effect of sodium-glucose\ncotransporter 2 inhibitors in patients with chronic\nkidney disease with or without type 2 diabetes\nmellitus on cardiovascular and renal outcomes: a\nsystematic review and meta-analysis. PLoS One\n2023;18:e0295059\n141. Herrington WG, Staplin N, Wanner C, et al.;\nEmpa-Kidney Collaborative Group. Empagli\ufb02ozin\nin patient\u2026[truncated]",
          "score": 0.7778655091764626
        },
        {
          "id": 11244357,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0249",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 249",
          "text": "Comorbidities,\u201d for further information on\nimmunization).\nPrevention\nThe only proven primary prevention inter-\nventions for CKD in people with diabetes\na r eb l o o dg l u c o s e( A 1 Cg o a lo f7 % )a n d\nblood pressure management. There is no\nevidence that renin-angiotensin-aldosterone\nsystem inhibitors or any other interventions\nprevent the development of CKD in the ab-\nsence of hypertension or albuminuria. Thus,\nthe American Diabetes Association does not\nreco\u2026[truncated]",
          "score": 0.7751223116967362
        },
        {
          "id": 11244358,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0250",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 250",
          "text": "T h ep r e s e n c eo fC K Da f f e c t st h er i s k s\nand bene\ufb01ts of intensive lowering of\nblood glucose and a number of speci\ufb01c\nglucose-lowering medications. Adverse\neffects of intensive management of\nblood glucose levels (hypoglycemia and\nmortality) were increased among people\nwith kidney disease at baseline (60).\nMoreover, there is a lag time of at least 2\nyears in type 2 diabetes to over 10 years\nin type 1 diabetes for the effects of in-\ntensive glucose cont\u2026[truncated]",
          "score": 0.7623590655876891
        },
        {
          "id": 11246262,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0102",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 102",
          "text": "appears to be irrespective of the level of GFR, with no\nevidence of a threshold level of eGFR below which ben-\ne\ufb01ts start to attenuate.\nFor the 1A recommendation (3.7.1), also see the 2022\nupdate to the KDIGO Clinical Practice Guideline in Diabetes\nManagement for details of the certainty of the evidence.\n23 Our\nERT speci\ufb01cally also undertook a systematic review limited to\npeople with CKD and no diabetes and considered the\ncertainty of the effect in this subgroup t\u2026[truncated]",
          "score": 0.7601894569058211
        }
      ],
      "ts_hits": [
        {
          "id": 11244308,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0200",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 200",
          "text": "leading to the recommendation that sem-\na g l u t i d ec a nb eu s e da sa n o t h e r\ufb01rst-line\nagent for people with CKD (137,138).\nOther GLP-1 RAs (liraglutide and dulaglu-\ntide) may also have CKD bene\ufb01ts, but no\nother dedicated kidney trials have been\npublished. Similarly, no dedicated kidney\noutcomes studies for the dual GIP and\nGLP-1 RA (tirzepatide) have been pub-\nlished. Dedicated kidney outcomes trials\nin people with CKD and type 2 diabetes\nhave shown that\u2026[truncated]",
          "score": 0.99999577
        },
        {
          "id": 11244357,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0249",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 249",
          "text": "Comorbidities,\u201d for further information on\nimmunization).\nPrevention\nThe only proven primary prevention inter-\nventions for CKD in people with diabetes\na r eb l o o dg l u c o s e( A 1 Cg o a lo f7 % )a n d\nblood pressure management. There is no\nevidence that renin-angiotensin-aldosterone\nsystem inhibitors or any other interventions\nprevent the development of CKD in the ab-\nsence of hypertension or albuminuria. Thus,\nthe American Diabetes Association does not\nreco\u2026[truncated]",
          "score": 0.9971815
        },
        {
          "id": 11244307,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0199",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 199",
          "text": "with A1C levels 1.5\u20132.0% above their indi-\nvidualized goal. Finally, incorporation\nof high-glycemic-ef \ufb01cacy therapies or\ntherapies for cardiovascular and kidney\ndisease risk reduction (e.g., GLP-1 RAs,\ndual GIP and GLP-1 RA, and SGLT2 inhibi-\ntors) may reduce the need for agents that\nincrease the risks of hypoglycemia and\nweight gain or are less well tolerated.\nThus, treatment intensi\ufb01cation requires\npurposeful selection of medications in\nalignment with multiple \u2026[truncated]",
          "score": 0.9969699
        },
        {
          "id": 11244160,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0052",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 52",
          "text": "early childhood diabetes: The Environmental\nDeterminants of Diabetes in the Young (TEDDY).\nDiabetes Care 2015;38:808\u2013813\n54. McKeigue PM, Spiliopoulou A, McGurnaghan\nS, et al. Persistent C-peptide secretion in type 1\ndiabetes and its relationship to the genetic\narchitecture of diabetes. BMC Med 2019;17:165\n55. Sosenko JM, Palmer JP , Rafkin-Mervis L,\net al.; Diabetes Prevention Trial-Type 1 Study\nGroup. Incident dysglycemia and progression to\ntype 1 diabetes among\u2026[truncated]",
          "score": 0.099297166
        },
        {
          "id": 11244414,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0306",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 306",
          "text": "10. Driscoll KA, Volkening LK, Haro H, et al. Are\nchildren with type 1 diabetes safe at school?\nExamining parent perceptions. Pediatr Diabetes\n2015;16:613\u2013620\n11. Cogen F, Rodriguez H, March CA, et al.\nDiabetes care in the school setting: a statement\nof the American Diabetes Association. Diabetes\nCare 2024;47:2050\u20132061\n12. Mehta SN, Volkening LK, Anderson BJ, et al.;\nFamily Management of Childhood Diabetes\nStudy Steering Committee. Dietary behaviors\npredict glycem\u2026[truncated]",
          "score": 0.099254064
        },
        {
          "id": 11244228,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0120",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 120",
          "text": "sleep dif\ufb01culties, referral to sleep special-\nists to address the medical and behavioral\naspects of sleep is recommended, ideally\nin collaboration with the diabetes care\nteam (Fig. 5.2).\nReferences\n1. Young-Hyman D, de Groot M, Hill-Briggs F,\nGonzalez JS, Hood K, Peyrot M. Psychosocial care\nfor people with diabetes: a position statement of\nthe American Diabetes Association. Diabetes\nCare 2016;39:2126\u20132140\n2. Powers MA, Bardsley JK, Cypress M, et al.\nDiabetes self-\u2026[truncated]",
          "score": 0.099235296
        },
        {
          "id": 11246215,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0055",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 55",
          "text": "and transplantation).56 A public health approach toward CKD\ndetection and treatment could reduce inequities in the burden\nof kidney failure by slowing the rate of progression and the\nrisk of CVD for everyone.\n57\nThe possible harm of early detection of CKD is that the\nnew diagnosis may cause anxiety in some people, particularly\nif the testing is not discussed in advance of the results. Dis-\ncussions around disease detection are common in the primary\ncare setting, a\u2026[truncated]",
          "score": 0.098602496
        },
        {
          "id": 11246250,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0090",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 90",
          "text": "Chapter 3: Delaying CKD progression and managing\nits complications\n3.1 CKD treatment and risk modi\ufb01cation\nPractice Point 3.1.1: Treat people with CKD with a\ncomprehensive treatment strategy to reduce risks of\nprogression of CKD and its associated complications\n(Figure 17).\nRisk factors associated with CKD progression, CVD, and\nother CKD complications are highly interrelated,\n435 and\nhence so is their management. We use the term \u201cCKD\ntreatment and risk modi\ufb01cation\u201d\u2026[truncated]",
          "score": 0.098287635
        }
      ],
      "overlap": {
        "semantic_only": [
          11244318,
          11244358,
          11244359,
          11246259,
          11246260,
          11246262
        ],
        "ts_only": [
          11244160,
          11244228,
          11244307,
          11244414,
          11246215,
          11246250
        ],
        "both": [
          11244308,
          11244357
        ],
        "jaccard": 0.14285714285714285
      },
      "llm": {
        "error": "500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat",
        "model": "eoh-llama:70b"
      },
      "batch_index": 2
    },
    {
      "query": "Which agents reduce renal outcomes in diabetic kidney disease?",
      "top_k": 8,
      "sources_filter": null,
      "embed_model": "BAAI/bge-base-en-v1.5",
      "pilot_slice_source_reference": {
        "rxnorm": "NLM RxNorm drug and ingredient concepts (RxCUI, names, TTYs).",
        "loinc": "LOINC laboratory and clinical observation codes with long names.",
        "hpo": "Human Phenotype Ontology terms (phenotypes, disease manifestations).",
        "snomed": "SNOMED CT clinical concepts (disorders, findings, procedures).",
        "icd10cm": "ICD-10-CM diagnosis codes and official long titles (US clinical modification).",
        "icd11": "WHO ICD-11 foundation mortality and morbidity content mirrored for search.",
        "orphanet": "Orphanet rare disease names, synonyms, and classification text.",
        "chv": "Consumer Health Vocabulary \u2014 lay-language terms linked to clinical concepts (UMLS CHV).",
        "va_guidelines": "VA/DoD clinical practice guideline sections ingested as rag_corpus chunks.",
        "acc_aha_valvular_2020": "2020 ACC/AHA guideline on valvular heart disease (chunked text).",
        "ada_dm_2024": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage).",
        "kdigo_ckd_2021": "KDIGO 2021 clinical practice guideline for chronic kidney disease (CKD).",
        "kdigo_ckd_2024": "KDIGO 2024 CKD evaluation and management guideline excerpts.",
        "kdigo_gn_ln_2021": "KDIGO 2021 guideline for glomerular diseases including lupus nephritis.",
        "kdigo_anemia_ckd_2023": "KDIGO 2023 clinical practice guideline for anemia in CKD.",
        "gold_copd_2023": "GOLD 2023 Global Strategy for Diagnosis, Management, and Prevention of COPD.",
        "gold_copd_2024": "GOLD 2024 COPD strategy document excerpts.",
        "gina_asthma_2023": "GINA 2023 Global Strategy for Asthma Management and Prevention.",
        "cdc_opioid": "CDC opioid prescribing guideline narrative sections (structured plain text).",
        "acr_eular": "Joint ACR/EULAR classification or criteria publications (combined tag).",
        "acr_ild_2023": "ACR guidance on idiopathic inflammatory myopathies with ILD (2023).",
        "acr_ra_2021": "ACR guideline or guidance on rheumatoid arthritis management (2021).",
        "acr_npf_psa_2018": "ACR/NPF joint guideline on psoriasis and psoriatic arthritis (2018).",
        "acr_vf_anca_2021": "ACR/VF guideline on ANCA-associated vasculitis (2021).",
        "acr_reproductive_health_2020": "ACR reproductive health guidance for rheumatic disease (2020).",
        "eular_acr_sle_2019": "EULAR/ACR classification criteria or lupus management collaboration (2019).",
        "eular_ra_2022": "EULAR recommendations for rheumatoid arthritis management (2022).",
        "eular_psa_2020": "EULAR recommendations for psoriatic arthritis pharmacologic therapy (2020).",
        "eular_sle_nephritis_2025": "EULAR recommendations on management of lupus nephritis (2025).",
        "eular_anca_2022": "EULAR recommendations for ANCA-associated vasculitis (2022).",
        "eular_lvv_2018": "EULAR recommendations for large-vessel vasculitis (2018).",
        "eular_axspa_2022": "EULAR recommendations for axial spondyloarthritis (2022).",
        "asas_eular_axspa_2022": "ASAS\u2013EULAR recommendations for axial spondyloarthritis (2022).",
        "diagrules": "Curated diagnostic-rule narrative cards used as RAG chunks.",
        "eoh_canon_v6": "Ethos of Health canon v6 narrative chunks (foundational clinical ethos text).",
        "eoh_2025": "Ethos of Health 2025 corpus excerpts in rag_corpus.",
        "eoh_gold_2025": "Ethos of Health \u00d7 GOLD COPD 2025 cross-reference or summary chunks.",
        "ethos_model": "Short Ethos-of-Health model or meta documents (small row count)."
      },
      "router_plan": {
        "question_type": "D",
        "semantic_query": "Agents that reduce renal outcomes in diabetic kidney disease include medications such as canagliflozin and empagliflozin, which are used to slow the progression of kidney disease by reducing proteinuria. These agents work by inhibiting the reabsorption of glucose in the kidneys, leading to a decrease in blood sugar levels and a reduction in the amount of protein that is filtered through the kidneys. Additionally, some medications such as SGLT2 inhibitors have been shown to reduce renal outcomes in patients with diabetic kidney disease by reducing inflammation and improving blood flow to the kidneys.",
        "ts_query": "(canagliflozin OR empagliflozin) AND (diabetic kidney disease OR proteinuria)",
        "ts_terms": [
          "canagliflozin",
          "empagliflozin",
          "diabetic kidney disease",
          "proteinuria"
        ],
        "selected_sources": [
          {
            "source": "ada_dm_2024",
            "priority": 1,
            "why": "American Diabetes Association Standards of Care provides evidence on the use of canagliflozin and empagliflozin in patients with diabetic kidney disease."
          },
          {
            "source": "kdigo_ckd_2021",
            "priority": 2,
            "why": "KDIGO 2021 clinical practice guideline for chronic kidney disease includes recommendations for the use of SGLT2 inhibitors in patients with diabetic kidney disease."
          },
          {
            "source": "cdc_opioid",
            "priority": 3,
            "why": "CDC opioid prescribing guideline narrative sections provide information on the potential benefits and risks of using canagliflozin and empagliflozin in patients with diabetic kidney disease."
          }
        ],
        "selected_modules": [
          {
            "module_id": "M13",
            "priority": 1,
            "why": "Trend & Prognostic Engine is able to compute flare probabilities and risk trajectories for patients with diabetic kidney disease."
          },
          {
            "module_id": "M14",
            "priority": 2,
            "why": "Action & Escalation Engine can determine concrete next steps for both patient and clinician given a forecast of renal outcomes in diabetic kidney disease."
          }
        ],
        "notes": "These agents have been shown to reduce renal outcomes in patients with diabetic kidney disease by slowing the progression of kidney disease and reducing inflammation.",
        "elapsed_sec": 4.07,
        "model": "eoh-llama3.2-source-router"
      },
      "effective_sources": [
        "ada_dm_2024",
        "kdigo_ckd_2021",
        "cdc_opioid"
      ],
      "embed_device": "cuda",
      "embed_text": "Agents that reduce renal outcomes in diabetic kidney disease include medications such as canagliflozin and empagliflozin, which are used to slow the progression of kidney disease by reducing proteinuria. These agents work by inhibiting the reabsorption of glucose in the kidneys, leading to a decrease in blood sugar levels and a reduction in the amount of protein that is filtered through the kidneys. Additionally, some medications such as SGLT2 inhibitors have been shown to reduce renal outcomes in patients with diabetic kidney disease by reducing inflammation and improving blood flow to the kidneys.",
      "embed_sec": 2.2776,
      "db_sec": 0.0351,
      "ts_strategy": "per_term (4 terms)",
      "ts_terms_used": [
        "canagliflozin",
        "empagliflozin",
        "diabetic kidney disease",
        "proteinuria"
      ],
      "semantic_hits": [
        {
          "id": 11244318,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0210",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 210",
          "text": "diabetes: a meta-analysis. JAMA Cardiol 2021;6:\n148\u2013158\n140. Reyes-Farias CI, Reategui-Diaz M, Romani-\nRomani F, Prokop L. The effect of sodium-glucose\ncotransporter 2 inhibitors in patients with chronic\nkidney disease with or without type 2 diabetes\nmellitus on cardiovascular and renal outcomes: a\nsystematic review and meta-analysis. PLoS One\n2023;18:e0295059\n141. Herrington WG, Staplin N, Wanner C, et al.;\nEmpa-Kidney Collaborative Group. Empagli\ufb02ozin\nin patient\u2026[truncated]",
          "score": 0.7827217837903757
        },
        {
          "id": 11244308,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0200",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 200",
          "text": "leading to the recommendation that sem-\na g l u t i d ec a nb eu s e da sa n o t h e r\ufb01rst-line\nagent for people with CKD (137,138).\nOther GLP-1 RAs (liraglutide and dulaglu-\ntide) may also have CKD bene\ufb01ts, but no\nother dedicated kidney trials have been\npublished. Similarly, no dedicated kidney\noutcomes studies for the dual GIP and\nGLP-1 RA (tirzepatide) have been pub-\nlished. Dedicated kidney outcomes trials\nin people with CKD and type 2 diabetes\nhave shown that\u2026[truncated]",
          "score": 0.7826160918106992
        },
        {
          "id": 11244305,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0197",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 197",
          "text": "Table 9.2\u2014Features of medications for lowering glucose in type 2 diabetes\nMedication \n(route of \nadministration)\nGlucose-\nlowering \nefficacy1\nHypoglycemia \nrisk Weight effects\n2\nCV effects Kidney effects\nMASH \neffects Clinical considerations and adverse effectsEffect on MACE Effect on HF\nProgression of \nCKD Dosing/use considerations*\nMetformin\n(\noral)\nHigh No Neutral \n(potential for \nmodest loss)\nPotential\nbenefit\nNeutral Neutral \u2022 Contraindicated with \neGFR <30 m\u2026[truncated]",
          "score": 0.7817438970956878
        },
        {
          "id": 11244359,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0251",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 251",
          "text": "activity (92\u201394). Glucagon-like peptide 1\n(GLP-1) receptor agonists (RAs) have\nalso been shown to improve kidney out-\ncomes (95\u2013100). Kidney effects should\nbe considered when selecting agents\nfor glucose lowering (see Section 9,\n\u201cPharmacologic Approaches to Glycemic\nTreatment\u201d).\nSelection of Glucose-Lowering\nMedications for People With Chronic\nKidney Disease\nFor people with type 2 diabetes and es-\ntablished CKD, special considerations for\nthe selection of glucose-\u2026[truncated]",
          "score": 0.7676904430297234
        },
        {
          "id": 11244357,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0249",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 249",
          "text": "Comorbidities,\u201d for further information on\nimmunization).\nPrevention\nThe only proven primary prevention inter-\nventions for CKD in people with diabetes\na r eb l o o dg l u c o s e( A 1 Cg o a lo f7 % )a n d\nblood pressure management. There is no\nevidence that renin-angiotensin-aldosterone\nsystem inhibitors or any other interventions\nprevent the development of CKD in the ab-\nsence of hypertension or albuminuria. Thus,\nthe American Diabetes Association does not\nreco\u2026[truncated]",
          "score": 0.7652539154735868
        },
        {
          "id": 11244358,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0250",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 250",
          "text": "T h ep r e s e n c eo fC K Da f f e c t st h er i s k s\nand bene\ufb01ts of intensive lowering of\nblood glucose and a number of speci\ufb01c\nglucose-lowering medications. Adverse\neffects of intensive management of\nblood glucose levels (hypoglycemia and\nmortality) were increased among people\nwith kidney disease at baseline (60).\nMoreover, there is a lag time of at least 2\nyears in type 2 diabetes to over 10 years\nin type 1 diabetes for the effects of in-\ntensive glucose cont\u2026[truncated]",
          "score": 0.7648250144928677
        },
        {
          "id": 11244360,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0252",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 252",
          "text": "at high risk for CVD or with existing CVD\nexamined kidney effects as secondary out-\ncomes. These trials include EMPA-REG\nOUTCOME [BI 10773 (Empagli\ufb02ozin) Car-\ndiovascular Outcome Event Trial in Type 2\nDiabetes Mellitus Patients], CANVAS\n(Canagli\ufb02ozin Cardiovascular Assessment\nStudy), LEADER (Liraglutide Effect and Ac-\ntion in Diabetes: Evaluation of Cardiovas-\ncular Outcome Results), and SUSTAIN-6\n(Trial to Evaluate Cardiovascular and\nOther Long-term Outcomes With\u2026[truncated]",
          "score": 0.7605487930938326
        },
        {
          "id": 11244365,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0257",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 257",
          "text": "receptor agonists and sodium-glucose cotrans-\nporter 2 inhibitors for prevention of major adverse\ncardiovascular and renal outcomes in type 2\ndiabetes mellitus. Circulation 2019;139:2022\u20132031\n108. Mann JFE, Hansen T, Idorn T, et al. Effects\nof once-weekly subcutaneous semaglutide on\nkidney function and safety in patients with type 2\ndiabetes: a post-hoc analysis of the SUSTAIN 1-7\nrandomised controlled trials. Lancet Diabetes\nEndocrinol 2020;8:880\u2013893\n109. Mann JF\u2026[truncated]",
          "score": 0.7596788836099727
        }
      ],
      "ts_hits": [
        {
          "id": 11246348,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0188",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 188",
          "text": "392. Lambers Heerspink HJ, Gansevoort RT. Albuminuria is an appropriate\ntherapeutic target in patients with CKD: the pro view. Clin J Am Soc\nNephrol. 2015;10:1079\u20131088.\n393. Fuhrman DY, Schneider MF, Dell KM, et al. Albuminuria, proteinuria, and\nrenal disease progression in children with CKD.Clin J Am Soc Nephrol.\n2017;12:912\u2013920.\n394. Harambat J, Kunzmann K, Azukaitis K, et al. Metabolic acidosis is\ncommon and associates with disease progression in children with\n\u2026[truncated]",
          "score": 0.9865413
        },
        {
          "id": 11244362,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0254",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 254",
          "text": "The primary composite outcome was\ncardiovascular death, myocardial infarc-\ntion, stroke, and hospitalization for heart\nfailure. The\ufb01nerenone group showed a\n13% reduction in the primary end point\ncompared with the placebo group (12.4%\nvs. 14.2%; HR 0.87 [95% CI 0.76\u20130.98];\nP =0 . 0 3 ) .T h i sb e n e\ufb01tw a sp r i m a r i l y\ndriven by a reduction in heart failure hos-\npitalizations: 3.2% vs. 4.4% in the placebo\ngroup (HR 0.71 [95% CI 0.56\u20130.90]).\nOf the secondary o\u2026[truncated]",
          "score": 0.95052516
        },
        {
          "id": 11246351,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0191",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 191",
          "text": "533. Bakris GL, Agarwal R, Anker SD, et al. Effect of\ufb01nerenone on chronic kidney\ndisease outcomes in type 2 diabetes.N Engl J Med. 2020;383:2219\u20132229.\n534. Pitt B, Filippatos G, Agarwal R, et al. Cardiovascular events with\n\ufb01nerenone in kidney disease and type 2 diabetes. N Engl J Med.\n2021;385:2252\u20132263.\n535. Agarwal R, Filippatos G, Pitt B, et al. Cardiovascular and kidney outcomes\nwith \ufb01nerenone in patients with type 2 diabetes and chronic kidney\ndisease: the FI\u2026[truncated]",
          "score": 0.93815774
        },
        {
          "id": 11246345,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0185",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 185",
          "text": "245. Eneanya ND, Adingwupu OM, Kostelanetz S, et al. Social determinants of\nhealth and their impact on the Black race coef\ufb01cient in serum creatinine-\nbased estimation of GFR: secondary analysis of MDRD and CRIC studies.\nClin J Am Soc Nephrol. 2023;18:446\u2013454.\n246. Borrell LN, Elhawary JR, Fuentes-Af\ufb02ick E, et al. Race and genetic ancestry\nin medicine\u2014 a time for reckoning with racism.N Engl J Med. 2021;384:\n474\u2013480.\n247. Oni-Orisan A, Mavura Y, Banda Y, et al. Emb\u2026[truncated]",
          "score": 0.09549889
        },
        {
          "id": 11246347,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0187",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 187",
          "text": "344. Incerti J, Zelmanovitz T, Camargo JL, et al. Evaluation of tests for\nmicroalbuminuria screening in patients with diabetes. Nephrol Dial\nTransplant. 2005;20:2402\u20132407.\n345. Kaiser C, Bergel F, Doehring-Schwerdtfeger E, et al. Urine test strips:\nreliability of semi-quantitative \ufb01ndings under tropical conditions.\nPediatr Nephrol. 1992;6:145\u2013148.\n346. Khawali C, Andriolo A, Ferreira SR. Comparison of methods for urinary\nalbumin determination in patients with type\u2026[truncated]",
          "score": 0.09421459
        },
        {
          "id": 11246238,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0078",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 78",
          "text": "better characterize proteinuria. Signi \ufb01cant albuminuria\ngenerally re\ufb02ects glomerular damage.304 Importantly, in the\ncontext of screening for children with diabetes, ACR\nremains the standard, in line with adult guidelines.\nThe same considerations of using \ufb01rst morning samples\n(because of orthostatic proteinuria) and considering tran-\nsiently increased proteinuria during intercurrent illness or\nafter exercise apply to children as well as adults. Orthostatic\nprotein\u2026[truncated]",
          "score": 0.09360665
        },
        {
          "id": 11246264,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0104",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 104",
          "text": "Special considerations\nPediatric considerations. SGLT2i have not been tested in\nclinical trials on children with kidney disease. Limited\nobservational data and phase II trial data exist for children\nwith and without kidney disease. Four studies (99 children\nand young adults with diabetes and normal GFR) found that\npharmacokinetics and pharmacodynamics were likely to be\nthe same in children and adults.\n525\u2013528 Recent work modeled\npediatric dapagli\ufb02ozin dosing for s\u2026[truncated]",
          "score": 0.08897689
        },
        {
          "id": 11244339,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0231",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 231",
          "text": "the odds of having PAD by 85% (235). No-\ntably, classical symptoms of claudication\nare uncommon, and almost half of people\nwith newly diagnosed PAD were asymp-\ntomatic (233). Conversely, up to two-\nthirds of people with asymptomatic PAD\nhave been shown to have comorbid dia-\nbetes (236). Risk factors associated with\nan increased risk for PAD in people with\ndiabetes include age, smoking, hyperten-\nsion, dyslipidemia, worse glycemic man-\nagement, longer duration of d\u2026[truncated]",
          "score": 0.08654518
        }
      ],
      "overlap": {
        "semantic_only": [
          11244305,
          11244308,
          11244318,
          11244357,
          11244358,
          11244359,
          11244360,
          11244365
        ],
        "ts_only": [
          11244339,
          11244362,
          11246238,
          11246264,
          11246345,
          11246347,
          11246348,
          11246351
        ],
        "both": [],
        "jaccard": 0.0
      },
      "llm": {
        "error": "500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat",
        "model": "eoh-llama:70b"
      },
      "batch_index": 3
    },
    {
      "query": "How is anemia in chronic kidney disease managed per KDIGO?",
      "top_k": 8,
      "sources_filter": null,
      "embed_model": "BAAI/bge-base-en-v1.5",
      "pilot_slice_source_reference": {
        "rxnorm": "NLM RxNorm drug and ingredient concepts (RxCUI, names, TTYs).",
        "loinc": "LOINC laboratory and clinical observation codes with long names.",
        "hpo": "Human Phenotype Ontology terms (phenotypes, disease manifestations).",
        "snomed": "SNOMED CT clinical concepts (disorders, findings, procedures).",
        "icd10cm": "ICD-10-CM diagnosis codes and official long titles (US clinical modification).",
        "icd11": "WHO ICD-11 foundation mortality and morbidity content mirrored for search.",
        "orphanet": "Orphanet rare disease names, synonyms, and classification text.",
        "chv": "Consumer Health Vocabulary \u2014 lay-language terms linked to clinical concepts (UMLS CHV).",
        "va_guidelines": "VA/DoD clinical practice guideline sections ingested as rag_corpus chunks.",
        "acc_aha_valvular_2020": "2020 ACC/AHA guideline on valvular heart disease (chunked text).",
        "ada_dm_2024": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage).",
        "kdigo_ckd_2021": "KDIGO 2021 clinical practice guideline for chronic kidney disease (CKD).",
        "kdigo_ckd_2024": "KDIGO 2024 CKD evaluation and management guideline excerpts.",
        "kdigo_gn_ln_2021": "KDIGO 2021 guideline for glomerular diseases including lupus nephritis.",
        "kdigo_anemia_ckd_2023": "KDIGO 2023 clinical practice guideline for anemia in CKD.",
        "gold_copd_2023": "GOLD 2023 Global Strategy for Diagnosis, Management, and Prevention of COPD.",
        "gold_copd_2024": "GOLD 2024 COPD strategy document excerpts.",
        "gina_asthma_2023": "GINA 2023 Global Strategy for Asthma Management and Prevention.",
        "cdc_opioid": "CDC opioid prescribing guideline narrative sections (structured plain text).",
        "acr_eular": "Joint ACR/EULAR classification or criteria publications (combined tag).",
        "acr_ild_2023": "ACR guidance on idiopathic inflammatory myopathies with ILD (2023).",
        "acr_ra_2021": "ACR guideline or guidance on rheumatoid arthritis management (2021).",
        "acr_npf_psa_2018": "ACR/NPF joint guideline on psoriasis and psoriatic arthritis (2018).",
        "acr_vf_anca_2021": "ACR/VF guideline on ANCA-associated vasculitis (2021).",
        "acr_reproductive_health_2020": "ACR reproductive health guidance for rheumatic disease (2020).",
        "eular_acr_sle_2019": "EULAR/ACR classification criteria or lupus management collaboration (2019).",
        "eular_ra_2022": "EULAR recommendations for rheumatoid arthritis management (2022).",
        "eular_psa_2020": "EULAR recommendations for psoriatic arthritis pharmacologic therapy (2020).",
        "eular_sle_nephritis_2025": "EULAR recommendations on management of lupus nephritis (2025).",
        "eular_anca_2022": "EULAR recommendations for ANCA-associated vasculitis (2022).",
        "eular_lvv_2018": "EULAR recommendations for large-vessel vasculitis (2018).",
        "eular_axspa_2022": "EULAR recommendations for axial spondyloarthritis (2022).",
        "asas_eular_axspa_2022": "ASAS\u2013EULAR recommendations for axial spondyloarthritis (2022).",
        "diagrules": "Curated diagnostic-rule narrative cards used as RAG chunks.",
        "eoh_canon_v6": "Ethos of Health canon v6 narrative chunks (foundational clinical ethos text).",
        "eoh_2025": "Ethos of Health 2025 corpus excerpts in rag_corpus.",
        "eoh_gold_2025": "Ethos of Health \u00d7 GOLD COPD 2025 cross-reference or summary chunks.",
        "ethos_model": "Short Ethos-of-Health model or meta documents (small row count)."
      },
      "router_plan": {
        "question_type": "OTHER",
        "semantic_query": "How is anemia in chronic kidney disease managed per KDIGO? The management of anemia in patients with chronic kidney disease (CKD) involves the use of erythropoiesis-stimulating agents (ESAs), iron supplementation, and other interventions. The Kidney Disease: Improving Global Outcomes (KDIGO) guidelines provide recommendations for the diagnosis, treatment, and monitoring of anemia in CKD patients.",
        "ts_query": "(anemia AND chronic kidney disease) OR (erythropoiesis-stimulating agents AND CKD)",
        "ts_terms": [
          "anemia",
          "chronic kidney disease",
          "erythropoiesis-stimulating agents",
          "KDIGO"
        ],
        "selected_sources": [
          {
            "source": "kdigo_ckd_2021",
            "priority": 1,
            "why": "KDIGO 2021 clinical practice guideline for chronic kidney disease (CKD) provides recommendations for the management of anemia in CKD patients."
          },
          {
            "source": "ada_dm_2024",
            "priority": 2,
            "why": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage) includes guidelines for the management of anemia in patients with diabetes and CKD."
          },
          {
            "source": "kdigo_anemia_ckd_2023",
            "priority": 3,
            "why": "KDIGO 2023 clinical practice guideline for anemia in CKD provides recommendations for the diagnosis, treatment, and monitoring of anemia in CKD patients."
          }
        ],
        "selected_modules": [
          {
            "module_id": "M13",
            "priority": 1,
            "why": "Trend & Prognostic Engine can answer questions about flare risk over next X days/months or is trajectory improving/worsening and why?"
          }
        ],
        "notes": "The management of anemia in chronic kidney disease involves the use of erythropoiesis-stimulating agents (ESAs), iron supplementation, and other interventions. The KDIGO guidelines provide recommendations for the diagnosis, treatment, and monitoring of anemia in CKD patients.",
        "elapsed_sec": 3.863,
        "model": "eoh-llama3.2-source-router"
      },
      "effective_sources": [
        "kdigo_ckd_2021",
        "ada_dm_2024",
        "kdigo_anemia_ckd_2023"
      ],
      "embed_device": "cuda",
      "embed_text": "How is anemia in chronic kidney disease managed per KDIGO? The management of anemia in patients with chronic kidney disease (CKD) involves the use of erythropoiesis-stimulating agents (ESAs), iron supplementation, and other interventions. The Kidney Disease: Improving Global Outcomes (KDIGO) guidelines provide recommendations for the diagnosis, treatment, and monitoring of anemia in CKD patients.",
      "embed_sec": 2.2909,
      "db_sec": 0.0493,
      "ts_strategy": "per_term (4 terms)",
      "ts_terms_used": [
        "anemia",
        "chronic kidney disease",
        "erythropoiesis-stimulating agents",
        "KDIGO"
      ],
      "semantic_hits": [
        {
          "id": 11243768,
          "source": "kdigo_anemia_ckd_2023",
          "source_id": "kdigo_anemia_ckd_2023:p0016",
          "title": "KDIGO 2023 Clinical Practice Guideline for Anemia in CKD \u2013 page 16",
          "text": "xvi \n \nABSTRACT \n \nThe Kidney Disease: Improving Global Outcomes (KDIGO) 2025 Clinical Practice Guideline \nfor Anemia in Chronic Kidney Disease (CKD) is an update of the KDIGO 2012 guideline on the topic. \nThe guideline informs the care of adults and children with anemia and CKD, whether treated with \nkidney replacement or not. The guideline includes chapters dedicated to diagnosis and evaluation of \niron deficiency and anemia in CKD, use of iron to treat iron def\u2026[truncated]",
          "score": 0.8719893846524557
        },
        {
          "id": 11243785,
          "source": "kdigo_anemia_ckd_2023",
          "source_id": "kdigo_anemia_ckd_2023:p0033",
          "title": "KDIGO 2023 Clinical Practice Guideline for Anemia in CKD \u2013 page 33",
          "text": "xvii \n \nPractice Point 4.6: Consider implementing strategies at the individual, organizational, and public \nhealth policy levels to reduce RBC transfusions in people with CKD (Table 11). \n \nTable 11 | Strategies to reduce red blood cells (RBC) transfusions in people with chronic kidney \ndisease (CKD) \n\u2022 Opt for less invasive procedures in hospitalized patients whenever possible. \n\u2022 Limit phlebotomy when medically appropriate. \n\u2022 Continue ESA/HIF-PHI/iron therapy i\u2026[truncated]",
          "score": 0.8314641419415235
        },
        {
          "id": 11243858,
          "source": "kdigo_anemia_ckd_2023",
          "source_id": "kdigo_anemia_ckd_2023:p0106",
          "title": "KDIGO 2023 Clinical Practice Guideline for Anemia in CKD \u2013 page 106",
          "text": "90 \n \n \nFigure 13 | Algorithm for guiding the use of red blood cell (RBC) transfusion to treat \nanemia in people with chronic kidney disease. ESA, erythropoiesis-stimulating agent; Hb, \nhemoglobin; TACO, transfusion-associated circulatory overload; TRALi, transfusion-related acute lung \ninjury. \n \nPractice Point 4.6: Consider implementing strategies at the individual, organizational, and \npublic health policy levels to reduce RBC transfusions in people with CKD (T\u2026[truncated]",
          "score": 0.828382750942385
        },
        {
          "id": 11243764,
          "source": "kdigo_anemia_ckd_2023",
          "source_id": "kdigo_anemia_ckd_2023:p0012",
          "title": "KDIGO 2023 Clinical Practice Guideline for Anemia in CKD \u2013 page 12",
          "text": "xii \n \nABBREVIATIONS AND ACRONYMS \n \nAABB Association for the Advancement of Blood & Biotherapies \nACEi angiotensin-converting enzyme inhibitor \nAGA American Gastroenterological Association \nARB angiotensin II receptor blocker \nBIA bioimpedance analysis \nCBC complete blood count \nCKD chronic kidney disease \nCHOIR Correction of Hemoglobin and Outcomes in Renal Insufficiency \nCKD G5HD chronic kidney disease stage G5 receiving hemodialysis \nCKD G5PD chronic kidney di\u2026[truncated]",
          "score": 0.8269142118794724
        },
        {
          "id": 11243864,
          "source": "kdigo_anemia_ckd_2023",
          "source_id": "kdigo_anemia_ckd_2023:p0112",
          "title": "KDIGO 2023 Clinical Practice Guideline for Anemia in CKD \u2013 page 112",
          "text": "96 \n \n\u2022 Important outcomes: Growth, height, weight, and cognitive development in pediatric studies; blood transfusion; \nhypertension or change in blood pressure; cancer; Hb: change in Hb, % patients reaching target Hb, mean Hb; \niron use and dose \nStudy design RCTs \nExisting systematic \nreview data included \nKDIGO Clinical Practice Guideline for Anemia in Chronic Kidney Disease Kidney Int Suppl (2011). 2012 Aug;2: \n279151 \n \nChung EYM, Palmer SC, Saglimbene VM, Cr\u2026[truncated]",
          "score": 0.8237186880447103
        },
        {
          "id": 11243860,
          "source": "kdigo_anemia_ckd_2023",
          "source_id": "kdigo_anemia_ckd_2023:p0108",
          "title": "KDIGO 2023 Clinical Practice Guideline for Anemia in CKD \u2013 page 108",
          "text": "92 \n \nMETHODS FOR GUIDELINE DEVELOPMENT \n \nAim \nThe aim of this project was to update the KDIGO 2012 Clinical Practice \nGuideline for Anemia in Chronic Kidney Disease.151 The guideline development methods \nare described below. \n \nOverview of the Process \nThis guideline adhered to international best practices for guideline development \n(Appendix B: Supplementary Table S2 and Table S3)333, 334 and have been reported in \naccordance with the AGREE II reporting checkli\u2026[truncated]",
          "score": 0.8205605470131864
        },
        {
          "id": 11243804,
          "source": "kdigo_anemia_ckd_2023",
          "source_id": "kdigo_anemia_ckd_2023:p0052",
          "title": "KDIGO 2023 Clinical Practice Guideline for Anemia in CKD \u2013 page 52",
          "text": "36 \n \nCKD, chronic kidney disease; ESA, erythropoietin-stimulating agents; Hb, hemoglobin; QoL, quality \nof life; TSAT, transferrin saturation \n \nResource use and costs \nIron supplementation seems to reduce the requirement for ESA therapy. Given the \nhigh cost of ESAs, appropriate use of iron in people with CKD would be expected to reduce \noverall costs.  \n \nConsiderations for implementation \nOral iron is inexpensive and readily available in most parts of the worl\u2026[truncated]",
          "score": 0.8193005782991222
        },
        {
          "id": 11243906,
          "source": "kdigo_anemia_ckd_2023",
          "source_id": "kdigo_anemia_ckd_2023:p0154",
          "title": "KDIGO 2023 Clinical Practice Guideline for Anemia in CKD \u2013 page 154",
          "text": "138 \n \nAppendix Figure 3. Management of anemia in CKD G5PD",
          "score": 0.8186375227026615
        }
      ],
      "ts_hits": [
        {
          "id": 11246340,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0180",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 180",
          "text": "References\n1. Kidney Disease: Improving Global Outcomes CKD Work Group. KDIGO\n2012 clinical practice guideline for the evaluation and management of\nchronic kidney disease.Kidney Int Suppl. 2012;3:S1\u2013S150.\n2. National Kidney Foundation. K/DOQI clinical practice guidelines for\nchronic kidney disease: evaluation, classi\ufb01cation, and strati\ufb01cation. Am\nJ Kidney Dis. 2002;39(suppl 1):S1\u2013S266.\n3. Levey AS, de Jong PE, Coresh J, et al. The de\ufb01nition, classi\ufb01cation, and\npro\u2026[truncated]",
          "score": 0.9999939
        },
        {
          "id": 11246348,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0188",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 188",
          "text": "392. Lambers Heerspink HJ, Gansevoort RT. Albuminuria is an appropriate\ntherapeutic target in patients with CKD: the pro view. Clin J Am Soc\nNephrol. 2015;10:1079\u20131088.\n393. Fuhrman DY, Schneider MF, Dell KM, et al. Albuminuria, proteinuria, and\nrenal disease progression in children with CKD.Clin J Am Soc Nephrol.\n2017;12:912\u2013920.\n394. Harambat J, Kunzmann K, Azukaitis K, et al. Metabolic acidosis is\ncommon and associates with disease progression in children with\n\u2026[truncated]",
          "score": 0.9999268
        },
        {
          "id": 11246358,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0198",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 198",
          "text": "858. Lu PH, Chung CH, Chuo HE, et al. Ef\ufb01cacy of acupoint stimulation as a\ntreatment for uremic pruritus: a systematic review and meta-analysis.\nFront Med (Lausanne). 2022;9:1036072.\n859. Simonsen E, Komenda P, Lerner B, et al. Treatment of uremic pruritus: a\nsystematic review. Am J Kidney Dis. 2017;70:638\u2013655.\n860. Mettang T, Kremer AE. Uremic pruritus.Kidney Int. 2015;87:685\u2013691.\n861. Manenti L, Tansinda P, Vaglio A. Uraemic pruritus: clinical characteristics,\np\u2026[truncated]",
          "score": 0.99948287
        },
        {
          "id": 11243789,
          "source": "kdigo_anemia_ckd_2023",
          "source_id": "kdigo_anemia_ckd_2023:p0037",
          "title": "KDIGO 2023 Clinical Practice Guideline for Anemia in CKD \u2013 page 37",
          "text": "21 \n \n \nFigure 2 | Mechanisms underlying anemia of CKD. Red color arrows are inhibitory and the \nblue arrows are stimulatory. EPO, erythropoietin; ESA, erythropoiesis-stimulating agents; ERFE, \nerythroferrone; ESA, erythropoiesis-stimulating agents; HIF-PHI, hypoxia-inducible factor\u2013prolyl \nhydroxylase inhibitors; RBC, red blood cell. Modified from Babitt et al.29 \n \nOutcomes associated with anemia in CKD \nAnemia in CKD is associated with several adverse cardiovas\u2026[truncated]",
          "score": 0.8837523
        },
        {
          "id": 11243897,
          "source": "kdigo_anemia_ckd_2023",
          "source_id": "kdigo_anemia_ckd_2023:p0145",
          "title": "KDIGO 2023 Clinical Practice Guideline for Anemia in CKD \u2013 page 145",
          "text": "129 \n \n264. Bradbury BD, Danese MD, Gleeson M, et al. Effect of Epoetin alfa dose changes on \nhemoglobin and mortality in hemodialysis patients with hemoglobin levels persistently \nbelow 11 g/dL. Clin J Am Soc Nephrol 2009; 4: 630-637. \n \n265. Kainz A, Mayer B, Kramar R, et al. Association of ESA hypo-responsiveness and \nhaemoglobin variability with mortality in haemodialysis patients. Nephrol Dial \nTransplant 2010; 25: 3701-3706. \n \n266. Kilpatrick RD, Critchlow \u2026[truncated]",
          "score": 0.8109226
        },
        {
          "id": 11243755,
          "source": "kdigo_anemia_ckd_2023",
          "source_id": "kdigo_anemia_ckd_2023:p0003",
          "title": "KDIGO 2023 Clinical Practice Guideline for Anemia in CKD \u2013 page 3",
          "text": "iii \n \nTABLES \nTable 1. Prevalence of anemia across CKD stages in different countries\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026. 19 \nTable 2. Factors to consider when choosing between oral and intravenous iron\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026.. 35 \nTable 3. Oral iron formulations, treatment regimen, and factors influencing the choice between different \nformulations\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026.. \n \n37 \nTable 4. Intravenous iron formulations and treatment regimen\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026 38 \nTable 5. Circ\u2026[truncated]",
          "score": 0.7927168
        },
        {
          "id": 11243759,
          "source": "kdigo_anemia_ckd_2023",
          "source_id": "kdigo_anemia_ckd_2023:p0007",
          "title": "KDIGO 2023 Clinical Practice Guideline for Anemia in CKD \u2013 page 7",
          "text": "vii \n \n Table S41. Adults with anemia and CKD receiving dialysis, ESA administered to reach a higher \nhemoglobin target versus ESA administered to reach a lower hemoglobin target, important outcomes... \n \nS87 \n Table S42. Adults with anemia, CKD, and heart failure, ESA administered to reach a lower \nhemoglobin target versus ESA administered to reach a higher hemoglobin target, important outcomes.. \n \nS89 \n Table S43. Adults with anemia and CKD not receiving dialys\u2026[truncated]",
          "score": 0.09761626
        },
        {
          "id": 11243758,
          "source": "kdigo_anemia_ckd_2023",
          "source_id": "kdigo_anemia_ckd_2023:p0006",
          "title": "KDIGO 2023 Clinical Practice Guideline for Anemia in CKD \u2013 page 6",
          "text": "vi \n \n Table S20. People with anemia and CKD receiving dialysis, HIF-PHI versus ESA, blood pressure \noutcomes\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026... \n \nS55 \n Table S21. People with anemia and CKD receiving dialysis, HIF-PHI versus ESA, hemoglobin \noutcomes\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026... \n \nS57 \n Table S22. People with anemia and CKD receiving dialysis, HIF-PHI versus ESA, transferrin \nsaturation\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026\u2026...\u2026.. \n \nS58 \n Table S23\u2026[truncated]",
          "score": 0.09729853
        }
      ],
      "overlap": {
        "semantic_only": [
          11243764,
          11243768,
          11243785,
          11243804,
          11243858,
          11243860,
          11243864,
          11243906
        ],
        "ts_only": [
          11243755,
          11243758,
          11243759,
          11243789,
          11243897,
          11246340,
          11246348,
          11246358
        ],
        "both": [],
        "jaccard": 0.0
      },
      "llm": {
        "error": "500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat",
        "model": "eoh-llama:70b"
      },
      "batch_index": 4
    },
    {
      "query": "What are GOLD 2024 escalation steps for COPD maintenance therapy?",
      "top_k": 8,
      "sources_filter": null,
      "embed_model": "BAAI/bge-base-en-v1.5",
      "pilot_slice_source_reference": {
        "rxnorm": "NLM RxNorm drug and ingredient concepts (RxCUI, names, TTYs).",
        "loinc": "LOINC laboratory and clinical observation codes with long names.",
        "hpo": "Human Phenotype Ontology terms (phenotypes, disease manifestations).",
        "snomed": "SNOMED CT clinical concepts (disorders, findings, procedures).",
        "icd10cm": "ICD-10-CM diagnosis codes and official long titles (US clinical modification).",
        "icd11": "WHO ICD-11 foundation mortality and morbidity content mirrored for search.",
        "orphanet": "Orphanet rare disease names, synonyms, and classification text.",
        "chv": "Consumer Health Vocabulary \u2014 lay-language terms linked to clinical concepts (UMLS CHV).",
        "va_guidelines": "VA/DoD clinical practice guideline sections ingested as rag_corpus chunks.",
        "acc_aha_valvular_2020": "2020 ACC/AHA guideline on valvular heart disease (chunked text).",
        "ada_dm_2024": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage).",
        "kdigo_ckd_2021": "KDIGO 2021 clinical practice guideline for chronic kidney disease (CKD).",
        "kdigo_ckd_2024": "KDIGO 2024 CKD evaluation and management guideline excerpts.",
        "kdigo_gn_ln_2021": "KDIGO 2021 guideline for glomerular diseases including lupus nephritis.",
        "kdigo_anemia_ckd_2023": "KDIGO 2023 clinical practice guideline for anemia in CKD.",
        "gold_copd_2023": "GOLD 2023 Global Strategy for Diagnosis, Management, and Prevention of COPD.",
        "gold_copd_2024": "GOLD 2024 COPD strategy document excerpts.",
        "gina_asthma_2023": "GINA 2023 Global Strategy for Asthma Management and Prevention.",
        "cdc_opioid": "CDC opioid prescribing guideline narrative sections (structured plain text).",
        "acr_eular": "Joint ACR/EULAR classification or criteria publications (combined tag).",
        "acr_ild_2023": "ACR guidance on idiopathic inflammatory myopathies with ILD (2023).",
        "acr_ra_2021": "ACR guideline or guidance on rheumatoid arthritis management (2021).",
        "acr_npf_psa_2018": "ACR/NPF joint guideline on psoriasis and psoriatic arthritis (2018).",
        "acr_vf_anca_2021": "ACR/VF guideline on ANCA-associated vasculitis (2021).",
        "acr_reproductive_health_2020": "ACR reproductive health guidance for rheumatic disease (2020).",
        "eular_acr_sle_2019": "EULAR/ACR classification criteria or lupus management collaboration (2019).",
        "eular_ra_2022": "EULAR recommendations for rheumatoid arthritis management (2022).",
        "eular_psa_2020": "EULAR recommendations for psoriatic arthritis pharmacologic therapy (2020).",
        "eular_sle_nephritis_2025": "EULAR recommendations on management of lupus nephritis (2025).",
        "eular_anca_2022": "EULAR recommendations for ANCA-associated vasculitis (2022).",
        "eular_lvv_2018": "EULAR recommendations for large-vessel vasculitis (2018).",
        "eular_axspa_2022": "EULAR recommendations for axial spondyloarthritis (2022).",
        "asas_eular_axspa_2022": "ASAS\u2013EULAR recommendations for axial spondyloarthritis (2022).",
        "diagrules": "Curated diagnostic-rule narrative cards used as RAG chunks.",
        "eoh_canon_v6": "Ethos of Health canon v6 narrative chunks (foundational clinical ethos text).",
        "eoh_2025": "Ethos of Health 2025 corpus excerpts in rag_corpus.",
        "eoh_gold_2025": "Ethos of Health \u00d7 GOLD COPD 2025 cross-reference or summary chunks.",
        "ethos_model": "Short Ethos-of-Health model or meta documents (small row count)."
      },
      "router_plan": {
        "question_type": "D",
        "semantic_query": "What are the GOLD 2024 escalation steps for COPD maintenance therapy? The strategy aims to improve patient outcomes by identifying and managing exacerbations. It emphasizes a step-wise approach, starting with mild exacerbations and progressing to more severe ones. The goal is to balance symptom control with quality of life and minimize the risk of hospitalization.",
        "ts_query": "(COPD OR \"Chronic Obstructive Pulmonary Disease\") AND (escalation OR management) AND (GOLD 2024 OR GOLD)",
        "ts_terms": [
          "COPD",
          "GOLD 2024",
          "escalation steps",
          "maintenance therapy"
        ],
        "selected_sources": [
          {
            "source": "gold_copd_2024",
            "priority": 1,
            "why": "Official GOLD 2024 strategy document"
          },
          {
            "source": "kdigo_ckd_2024",
            "priority": 2,
            "why": "KDIGO 2024 CKD evaluation and management guideline excerpts provide relevant information on COPD management"
          },
          {
            "source": "ada_dm_2024",
            "priority": 3,
            "why": "American Diabetes Association Standards of Care 2024 vintage provides guidance on managing comorbidities in COPD patients"
          }
        ],
        "selected_modules": [
          {
            "module_id": "M13",
            "priority": 1,
            "why": "Trend & Prognostic Engine is relevant for flare risk over next X days/months"
          },
          {
            "module_id": "M6",
            "priority": 2,
            "why": "Escalation Router / Central Switchboard helps choose severity tier and who should be notified based on state transitions"
          }
        ],
        "notes": "The GOLD 2024 strategy provides a step-wise approach to managing COPD exacerbations, emphasizing symptom control while balancing quality of life.",
        "elapsed_sec": 3.592,
        "model": "eoh-llama3.2-source-router"
      },
      "effective_sources": [
        "gold_copd_2024",
        "kdigo_ckd_2024",
        "ada_dm_2024"
      ],
      "embed_device": "cuda",
      "embed_text": "What are the GOLD 2024 escalation steps for COPD maintenance therapy? The strategy aims to improve patient outcomes by identifying and managing exacerbations. It emphasizes a step-wise approach, starting with mild exacerbations and progressing to more severe ones. The goal is to balance symptom control with quality of life and minimize the risk of hospitalization.",
      "embed_sec": 2.3629,
      "db_sec": 0.0633,
      "ts_strategy": "per_term (4 terms)",
      "ts_terms_used": [
        "COPD",
        "GOLD 2024",
        "escalation steps",
        "maintenance therapy"
      ],
      "semantic_hits": [
        {
          "id": 11242771,
          "source": "gold_copd_2024",
          "source_id": "gold_copd_2024:p0062",
          "title": "GOLD 2024 Global Strategy for the Prevention, Diagnosis and Management of COPD \u2013 page 62",
          "text": "Be sure to read and understand the paragraph entitled Important Purpose & Liability Disclaimer                                   51 \n \nFollow-up pharmacological management \nA separate algorithm is provided for FOLLOW-UP treatment, where the management is based on two key treatable \ntraits: persistence of dyspnea and occurrence of  exacerbations (Figure 3.9). These follow -up recommendations are \ndesigned to facilitate management of patients taking maintenance trea\u2026[truncated]",
          "score": 0.8277087416996131
        },
        {
          "id": 11242721,
          "source": "gold_copd_2024",
          "source_id": "gold_copd_2024:p0012",
          "title": "GOLD 2024 Global Strategy for the Prevention, Diagnosis and Management of COPD \u2013 page 12",
          "text": "Be sure to read and understand the paragraph entitled Important Purpose & Liability Disclaimer                                   1 \n \nGLOBAL STRATEGY FOR THE DIAGNOSIS, MANAGEMENT, \nAND PREVENTION OF COPD \nINTRODUCTION \nThe aim of the GOLD Report is to provide a non -biased review of the current evidence for the assessment, diagnosis \nand treatment of people with COPD. One of the strengths of GOLD reports is the treatment objectives. These have  \nstood the test of\u2026[truncated]",
          "score": 0.8038831224720187
        },
        {
          "id": 11242772,
          "source": "gold_copd_2024",
          "source_id": "gold_copd_2024:p0063",
          "title": "GOLD 2024 Global Strategy for the Prevention, Diagnosis and Management of COPD \u2013 page 63",
          "text": "Be sure to read and understand the paragraph entitled Important Purpose & Liability Disclaimer                                   52 \n \nThe follow-up pharmacological treatment algorithm (Figure 3.9) can be applied to any patient who is already taking \nmaintenance treatment(s) irrespective of the GOLD group allocated at treatment initiation. The need to target \nprimarily dyspnea/activity limitation or to prevent further exacerbations should be evaluate d in each pat\u2026[truncated]",
          "score": 0.7995321036500683
        },
        {
          "id": 11242761,
          "source": "gold_copd_2024",
          "source_id": "gold_copd_2024:p0052",
          "title": "GOLD 2024 Global Strategy for the Prevention, Diagnosis and Management of COPD \u2013 page 52",
          "text": "Be sure to read and understand the paragraph entitled Important Purpose & Liability Disclaimer                                   41 \n \nINTRODUCTION \nThe aim of COPD management is to reduce symptoms and future risk ( Figure 3.1). COPD patients should have an \nassessment of the severity of their airflow obstruction, symptoms, history of exacerbations, exposure to risk factors \nand comorbidities (see Chapter 2) to guide management. \n \n \n \nPharmacological and non-phar\u2026[truncated]",
          "score": 0.7868311190311114
        },
        {
          "id": 11242755,
          "source": "gold_copd_2024",
          "source_id": "gold_copd_2024:p0046",
          "title": "GOLD 2024 Global Strategy for the Prevention, Diagnosis and Management of COPD \u2013 page 46",
          "text": "Be sure to read and understand the paragraph entitled Important Purpose & Liability Disclaimer                                   35 \n \ndysfunction is a modifiable source of exercise intolerance  by rehabilitation.(469) A more detailed description of the \nmanagement of COPD and comorbidities is provided in Chapter 5. \nCombined initial COPD assessment \nIn 2011, GOLD proposed to move from the simple spirometric grading system  for disease severity assessment and \ntre\u2026[truncated]",
          "score": 0.7783805032032365
        },
        {
          "id": 11242768,
          "source": "gold_copd_2024",
          "source_id": "gold_copd_2024:p0059",
          "title": "GOLD 2024 Global Strategy for the Prevention, Diagnosis and Management of COPD \u2013 page 59",
          "text": "Be sure to read and understand the paragraph entitled Important Purpose & Liability Disclaimer                                   48 \n \nInitial pharmacotherapy should be based on the patient\u2019s GOLD group ( Figure 3.7).  Patients should be offered \nguidance and follow up on self-management of breathlessness, and stress management, and they should be given a \nwritten action plan (Figure 3.13).  Comorbidities should also be managed as per specific guidelines, irrespec\u2026[truncated]",
          "score": 0.7743926317223805
        },
        {
          "id": 11242819,
          "source": "gold_copd_2024",
          "source_id": "gold_copd_2024:p0110",
          "title": "GOLD 2024 Global Strategy for the Prevention, Diagnosis and Management of COPD \u2013 page 110",
          "text": "Be sure to read and understand the paragraph entitled Important Purpose & Liability Disclaimer                                   99 \n \nCHAPTER 4: MANAGEMENT OF EXACERBATIONS \nKEY POINTS: \n\u2022 An exacerbation of COPD is defined as an event characterized by dyspnea and/or cough \nand sputum that worsen over < 14 days. Exacerbations of COPD are often associated with \nincreased local and systemic inflammation caused by airway infection, pollution, or other \ninsults to th\u2026[truncated]",
          "score": 0.7709775840070798
        },
        {
          "id": 11242714,
          "source": "gold_copd_2024",
          "source_id": "gold_copd_2024:p0005",
          "title": "GOLD 2024 Global Strategy for the Prevention, Diagnosis and Management of COPD \u2013 page 5",
          "text": "Be sure to read and understand the paragraph entitled Important Purpose & Liability Disclaimer                                       iv \n \nGOLD 2024 REPORT HIGHLIGHTS \nThe GOLD report is revised annually and has been used worldwide by healthcare professionals as a tool to implement \neffective management programs based on local healthcare systems. \nIn the 2024 revision of the GOLD report several important changes have been made as follows:  \ni. Chapter 3 and Chapte\u2026[truncated]",
          "score": 0.7673245945782007
        }
      ],
      "ts_hits": [
        {
          "id": 11242714,
          "source": "gold_copd_2024",
          "source_id": "gold_copd_2024:p0005",
          "title": "GOLD 2024 Global Strategy for the Prevention, Diagnosis and Management of COPD \u2013 page 5",
          "text": "Be sure to read and understand the paragraph entitled Important Purpose & Liability Disclaimer                                       iv \n \nGOLD 2024 REPORT HIGHLIGHTS \nThe GOLD report is revised annually and has been used worldwide by healthcare professionals as a tool to implement \neffective management programs based on local healthcare systems. \nIn the 2024 revision of the GOLD report several important changes have been made as follows:  \ni. Chapter 3 and Chapte\u2026[truncated]",
          "score": 0.33588344
        },
        {
          "id": 11242716,
          "source": "gold_copd_2024",
          "source_id": "gold_copd_2024:p0007",
          "title": "GOLD 2024 Global Strategy for the Prevention, Diagnosis and Management of COPD \u2013 page 7",
          "text": "Be sure to read and understand the paragraph entitled Important Purpose & Liability Disclaimer                                       vi \n \npractice are cited in the GOLD report with preference given to citing the original randomized controlled trial(s). \n \nRecommendations by the GOLD Committees for use of any medication are based on the best evidence available from \nthe published literature and not on labeling directives from government regulators. The Committee d\u2026[truncated]",
          "score": 0.33149907
        },
        {
          "id": 11242713,
          "source": "gold_copd_2024",
          "source_id": "gold_copd_2024:p0004",
          "title": "GOLD 2024 Global Strategy for the Prevention, Diagnosis and Management of COPD \u2013 page 4",
          "text": "Be sure to read and understand the paragraph entitled Important Purpose & Liability Disclaimer  iii \nGLOBAL STRATEGY FOR THE DIAGNOSIS, MANAGEMENT, AND PREVENTION OF COPD  \n(2024) \nGOLD ASSEMBLY \nThe GOLD National Leaders are individuals from around the world with an interest in promoting the goals of GOLD \nwithin their home country. The group meets periodically to share information about programs of health education, \nCOPD management, and prevention. \nARGENTINA \n\u2026[truncated]",
          "score": 0.26650628
        },
        {
          "id": 11244303,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0195",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 195",
          "text": "metabolic dysfunction\u2013associated liver dis-\nease (MASLD) or metabolic dysfunction\u2013\nassociated steatohepatitis (MASH) risk (see\nSection 4,\u201cComprehensive Medical Evalu-\nation and Assessment of Comorbidities\u201d),\nand achievement and maintenance of\nindividualized glycemic goals. In general,\nhigher-ef\ufb01cacy approaches, including\ncombination therapy, have greater likeli-\nhood of achieving treatment goals. Weight\nmanagement is a distinct treatment goal,\nalong with glycemic \u2026[truncated]",
          "score": 0.13775244
        },
        {
          "id": 11242774,
          "source": "gold_copd_2024",
          "source_id": "gold_copd_2024:p0065",
          "title": "GOLD 2024 Global Strategy for the Prevention, Diagnosis and Management of COPD \u2013 page 65",
          "text": "Be sure to read and understand the paragraph entitled Important Purpose & Liability Disclaimer                                   54 \n \nthere is doubt, either check the inspiratory flow objectively(586,587) or switch to an MDI+/-spacer/VHC or SMI depending \non drug availability and patient\u2019s characteristics.  Suboptimal peak inspiratory flow and inhalation technique errors \nwere associated with higher COPD-related healthcare utilization and costs in patients on DPI\u2026[truncated]",
          "score": 0.09981878
        },
        {
          "id": 11242819,
          "source": "gold_copd_2024",
          "source_id": "gold_copd_2024:p0110",
          "title": "GOLD 2024 Global Strategy for the Prevention, Diagnosis and Management of COPD \u2013 page 110",
          "text": "Be sure to read and understand the paragraph entitled Important Purpose & Liability Disclaimer                                   99 \n \nCHAPTER 4: MANAGEMENT OF EXACERBATIONS \nKEY POINTS: \n\u2022 An exacerbation of COPD is defined as an event characterized by dyspnea and/or cough \nand sputum that worsen over < 14 days. Exacerbations of COPD are often associated with \nincreased local and systemic inflammation caused by airway infection, pollution, or other \ninsults to th\u2026[truncated]",
          "score": 0.09910323
        },
        {
          "id": 11242726,
          "source": "gold_copd_2024",
          "source_id": "gold_copd_2024:p0017",
          "title": "GOLD 2024 Global Strategy for the Prevention, Diagnosis and Management of COPD \u2013 page 17",
          "text": "Be sure to read and understand the paragraph entitled Important Purpose & Liability Disclaimer                                   6 \n \ncan contribute to COPD, that it can start early in life and affect young individuals, and that there are precursor \nconditions (Pre-COPD, PRISm), opens new windows of opportunity for its prevention, early diagnosis, and prompt and \nappropriate therapeutic intervention.(13) \n \nBURDEN OF COPD  \nCOPD is a leading cause of morbidity and\u2026[truncated]",
          "score": 0.09793941
        },
        {
          "id": 11242727,
          "source": "gold_copd_2024",
          "source_id": "gold_copd_2024:p0018",
          "title": "GOLD 2024 Global Strategy for the Prevention, Diagnosis and Management of COPD \u2013 page 18",
          "text": "Be sure to read and understand the paragraph entitled Important Purpose & Liability Disclaimer                                   7 \n \nconditions (e.g., cardiovascular disease, musculoskeletal impairment, diabetes mellitus)(42) that are related to smoking, \naging and/or COPD.(43)  \nMortality \nThe World Health Organization (WHO) publishes mortality statistics for selected causes of death annually for all WHO \nregions.(44) However, data must be interpreted with cauti\u2026[truncated]",
          "score": 0.09778958
        }
      ],
      "overlap": {
        "semantic_only": [
          11242721,
          11242755,
          11242761,
          11242768,
          11242771,
          11242772
        ],
        "ts_only": [
          11242713,
          11242716,
          11242726,
          11242727,
          11242774,
          11244303
        ],
        "both": [
          11242714,
          11242819
        ],
        "jaccard": 0.14285714285714285
      },
      "llm": {
        "error": "500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat",
        "model": "eoh-llama:70b"
      },
      "batch_index": 5
    },
    {
      "query": "What does GINA 2023 suggest for step-up asthma control?",
      "top_k": 8,
      "sources_filter": null,
      "embed_model": "BAAI/bge-base-en-v1.5",
      "pilot_slice_source_reference": {
        "rxnorm": "NLM RxNorm drug and ingredient concepts (RxCUI, names, TTYs).",
        "loinc": "LOINC laboratory and clinical observation codes with long names.",
        "hpo": "Human Phenotype Ontology terms (phenotypes, disease manifestations).",
        "snomed": "SNOMED CT clinical concepts (disorders, findings, procedures).",
        "icd10cm": "ICD-10-CM diagnosis codes and official long titles (US clinical modification).",
        "icd11": "WHO ICD-11 foundation mortality and morbidity content mirrored for search.",
        "orphanet": "Orphanet rare disease names, synonyms, and classification text.",
        "chv": "Consumer Health Vocabulary \u2014 lay-language terms linked to clinical concepts (UMLS CHV).",
        "va_guidelines": "VA/DoD clinical practice guideline sections ingested as rag_corpus chunks.",
        "acc_aha_valvular_2020": "2020 ACC/AHA guideline on valvular heart disease (chunked text).",
        "ada_dm_2024": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage).",
        "kdigo_ckd_2021": "KDIGO 2021 clinical practice guideline for chronic kidney disease (CKD).",
        "kdigo_ckd_2024": "KDIGO 2024 CKD evaluation and management guideline excerpts.",
        "kdigo_gn_ln_2021": "KDIGO 2021 guideline for glomerular diseases including lupus nephritis.",
        "kdigo_anemia_ckd_2023": "KDIGO 2023 clinical practice guideline for anemia in CKD.",
        "gold_copd_2023": "GOLD 2023 Global Strategy for Diagnosis, Management, and Prevention of COPD.",
        "gold_copd_2024": "GOLD 2024 COPD strategy document excerpts.",
        "gina_asthma_2023": "GINA 2023 Global Strategy for Asthma Management and Prevention.",
        "cdc_opioid": "CDC opioid prescribing guideline narrative sections (structured plain text).",
        "acr_eular": "Joint ACR/EULAR classification or criteria publications (combined tag).",
        "acr_ild_2023": "ACR guidance on idiopathic inflammatory myopathies with ILD (2023).",
        "acr_ra_2021": "ACR guideline or guidance on rheumatoid arthritis management (2021).",
        "acr_npf_psa_2018": "ACR/NPF joint guideline on psoriasis and psoriatic arthritis (2018).",
        "acr_vf_anca_2021": "ACR/VF guideline on ANCA-associated vasculitis (2021).",
        "acr_reproductive_health_2020": "ACR reproductive health guidance for rheumatic disease (2020).",
        "eular_acr_sle_2019": "EULAR/ACR classification criteria or lupus management collaboration (2019).",
        "eular_ra_2022": "EULAR recommendations for rheumatoid arthritis management (2022).",
        "eular_psa_2020": "EULAR recommendations for psoriatic arthritis pharmacologic therapy (2020).",
        "eular_sle_nephritis_2025": "EULAR recommendations on management of lupus nephritis (2025).",
        "eular_anca_2022": "EULAR recommendations for ANCA-associated vasculitis (2022).",
        "eular_lvv_2018": "EULAR recommendations for large-vessel vasculitis (2018).",
        "eular_axspa_2022": "EULAR recommendations for axial spondyloarthritis (2022).",
        "asas_eular_axspa_2022": "ASAS\u2013EULAR recommendations for axial spondyloarthritis (2022).",
        "diagrules": "Curated diagnostic-rule narrative cards used as RAG chunks.",
        "eoh_canon_v6": "Ethos of Health canon v6 narrative chunks (foundational clinical ethos text).",
        "eoh_2025": "Ethos of Health 2025 corpus excerpts in rag_corpus.",
        "eoh_gold_2025": "Ethos of Health \u00d7 GOLD COPD 2025 cross-reference or summary chunks.",
        "ethos_model": "Short Ethos-of-Health model or meta documents (small row count)."
      },
      "router_plan": {
        "question_type": "OTHER",
        "semantic_query": "GINA 2023 suggests step-up asthma control measures to improve patient outcomes. The Global Initiative for Asthma (GINA) provides evidence-based guidelines for managing asthma. What specific recommendations does GINA 2023 offer for step-up asthma control?",
        "ts_query": "(asthma OR bronchial disease) AND (step up OR intensify) AND (control OR management)",
        "ts_terms": [
          "asthma",
          "GINA",
          "step-up",
          "control"
        ],
        "selected_sources": [
          {
            "source": "gina_asthma_2023",
            "priority": 1,
            "why": "official guideline"
          },
          {
            "source": "cdc_opioid",
            "priority": 2,
            "why": "complementary guidance on asthma management"
          },
          {
            "source": "ada_dm_2024",
            "priority": 3,
            "why": "additional recommendations from the American Diabetes Association"
          }
        ],
        "selected_modules": [
          {
            "module_id": "M13",
            "priority": 1,
            "why": "flare detection and trend analysis"
          },
          {
            "module_id": "M6",
            "priority": 2,
            "why": "escalation routing and patient guidance"
          },
          {
            "module_id": "M12",
            "priority": 3,
            "why": "symptom narrative engine"
          }
        ],
        "notes": "GINA 2023 provides a comprehensive framework for managing asthma. The selected sources offer complementary guidance on step-up asthma control measures.",
        "elapsed_sec": 3.238,
        "model": "eoh-llama3.2-source-router"
      },
      "effective_sources": [
        "gina_asthma_2023",
        "cdc_opioid",
        "ada_dm_2024"
      ],
      "embed_device": "cuda",
      "embed_text": "GINA 2023 suggests step-up asthma control measures to improve patient outcomes. The Global Initiative for Asthma (GINA) provides evidence-based guidelines for managing asthma. What specific recommendations does GINA 2023 offer for step-up asthma control?",
      "embed_sec": 2.3814,
      "db_sec": 0.0521,
      "ts_strategy": "per_term (4 terms)",
      "ts_terms_used": [
        "asthma",
        "GINA",
        "step-up",
        "control"
      ],
      "semantic_hits": [
        {
          "id": 11246566,
          "source": "gina_asthma_2023",
          "source_id": "gina_asthma_2023:p0002",
          "title": "GINA 2023 Global Strategy for Asthma Management and Prevention \u2013 page 2",
          "text": "1 \n \n \n \nGlobal Strategy for Asthma Management and Prevention  \n(2023 update) \n \n \n \nThe reader acknowledges that this report is intended as an evidence-based asthma management strategy, for \nthe use of health professionals and policy-makers. It is based, to the best of our knowledge, on current best \nevidence and medical knowledge and practice at the date of publication. When assessing and treating patients, \nhealth professionals are strongly advised to use their\u2026[truncated]",
          "score": 0.8668638705854785
        },
        {
          "id": 11246767,
          "source": "gina_asthma_2023",
          "source_id": "gina_asthma_2023:p0203",
          "title": "GINA 2023 Global Strategy for Asthma Management and Prevention \u2013 page 203",
          "text": "202 8. Implementing asthma management strategies in health systems \nKEY POINTS  \n\u2022 In order to improve asthma care and patient outcomes, evidence-based recommendations must not only be \ndeveloped, but also disseminated and implemented at a national and local level, and integrated into clinical \npractice. \n\u2022 Recommendations for implementing asthma care strategies are based on many successful programs worldwide.  \n\u2022 Implementation requires an evidence-based strategy\u2026[truncated]",
          "score": 0.8654243865862139
        },
        {
          "id": 11246565,
          "source": "gina_asthma_2023",
          "source_id": "gina_asthma_2023:p0001",
          "title": "GINA 2023 Global Strategy for Asthma Management and Prevention \u2013 page 1",
          "text": "Global Strategy for\nAsthma Management and Prevention\nUpdated 2023\n\u00a9 2023 Global Initiative for Asthma\nCOPYRIGHTED MATERIAL - DO NOT COPY OR DISTRIBUTE",
          "score": 0.8610074089756777
        },
        {
          "id": 11246580,
          "source": "gina_asthma_2023",
          "source_id": "gina_asthma_2023:p0016",
          "title": "GINA 2023 Global Strategy for Asthma Management and Prevention \u2013 page 16",
          "text": "Methodology 15 \npeer-reviewed evidence and not on labeling directives from regulators.  \nFor existing therapies with evidence for new regimens or in different populations, the Science Committee may, where \nrelevant, make recommendations that are not necessarily covered by regulatory indications in any country at the time, \nprovided the Committee is satisfied with the available evidence around safety and efficacy/effectiveness. Since the \nGINA Strategy Report repre\u2026[truncated]",
          "score": 0.8555063777558414
        },
        {
          "id": 11246572,
          "source": "gina_asthma_2023",
          "source_id": "gina_asthma_2023:p0008",
          "title": "GINA 2023 Global Strategy for Asthma Management and Prevention \u2013 page 8",
          "text": "7 \nPreface \nAsthma is a serious global health problem affecting all age groups. Its prevalence is increasing in many countries, \nespecially among children. Although some countries have seen a decline in hospitalizations and deaths from asthma, \nasthma still imposes an unacceptable burden on health care systems, and on society through loss of productivity in the \nworkplace and, especially for pediatric asthma, disruption to the family. \nThis year, the Global Initia\u2026[truncated]",
          "score": 0.8499483287272905
        },
        {
          "id": 11246809,
          "source": "gina_asthma_2023",
          "source_id": "gina_asthma_2023:p0245",
          "title": "GINA 2023 Global Strategy for Asthma Management and Prevention \u2013 page 245",
          "text": "244 References \n885. Brouwers MC, Kho ME, Browman GP, et al. AGREE II: advancing guideline development, reporting and evaluation \nin health care. CMAJ 2010; 182: E839-842. \n886. Boulet LP, FitzGerald JM, Levy ML, et al. A guide to the translation of the Global Initiative for Asthma (GINA) \nstrategy into improved care. Eur Respir J 2012; 39: 1220-1229. \n887. Davis DA, Taylor-Vaisey A. Translating guidelines into practice. A systematic review of theoretic concepts, \u2026[truncated]",
          "score": 0.8488695115524837
        },
        {
          "id": 11246581,
          "source": "gina_asthma_2023",
          "source_id": "gina_asthma_2023:p0017",
          "title": "GINA 2023 Global Strategy for Asthma Management and Prevention \u2013 page 17",
          "text": "16 Abbreviations \nFUTURE CHALLENGES \nDespite laudable efforts to improve asthma care over the past 30 years, and the availability of effective medications, \nmany patients globally have not benefited from advances in asthma treatment and often lack even the rudiments of care. \nMany of the world\u2019s population live in areas with inadequate medical facilities and meager financial resources. GINA \nrecognizes that the recommendations found in this report must be adapted \u2026[truncated]",
          "score": 0.8410533165303891
        },
        {
          "id": 11246570,
          "source": "gina_asthma_2023",
          "source_id": "gina_asthma_2023:p0006",
          "title": "GINA 2023 Global Strategy for Asthma Management and Prevention \u2013 page 6",
          "text": "5 \nTables and figures \nDIAGNOSIS \nBox 1-1.  Diagnostic flowchart for clinical practice 24 \nBox 1-2.  Diagnostic criteria for asthma in adults, adolescents, and children 6\u201311 years 25 \nBox 1-3. Steps for confirming the diagnosis of asthma in a patient already taking ICS-containing treatment 28 \nBox 1-4.  How to step down ICS-containing treatment to help confirm the diagnosis of asthma 29 \nBox 1-5.  Differential diagnosis of asthma in adults, adolescents and childre\u2026[truncated]",
          "score": 0.8386782215450134
        }
      ],
      "ts_hits": [
        {
          "id": 11246646,
          "source": "gina_asthma_2023",
          "source_id": "gina_asthma_2023:p0082",
          "title": "GINA 2023 Global Strategy for Asthma Management and Prevention \u2013 page 82",
          "text": "3. Treating to control symptoms and minimize future risk  81 \nREVIEWING RESPONSE AND ADJUSTING TREATMENT  \nHow often should asthma be reviewed? \nPatients with asthma should be reviewed regularly to monitor their symptom control, risk factors and occurrence of \nexacerbations, as well as to document the response to any treatment changes. For most controller medications, \nimprovement in symptoms and lung function begins within days of initiating treatment, but the fu\u2026[truncated]",
          "score": 0.46501747
        },
        {
          "id": 11246745,
          "source": "gina_asthma_2023",
          "source_id": "gina_asthma_2023:p0181",
          "title": "GINA 2023 Global Strategy for Asthma Management and Prevention \u2013 page 181",
          "text": "180 6. Diagnosis and management of asthma in children 5 years and younger  \nWhich children should be prescribed regular controller treatment? \nIntermittent or episodic wheezing of any severity may represent an isolated viral-induced wheezing episode, an episode \nof seasonal or allergen-induced asthma, or unrecognized uncontrolled asthma. The initial treatment of wheezing is \nidentical for all of these \u2013 a SABA every 4\u20136 hours as needed until symptoms disappear, us\u2026[truncated]",
          "score": 0.3415071
        },
        {
          "id": 11246602,
          "source": "gina_asthma_2023",
          "source_id": "gina_asthma_2023:p0038",
          "title": "GINA 2023 Global Strategy for Asthma Management and Prevention \u2013 page 38",
          "text": "2. Assessment of asthma 37 \nNumerical \u2018asthma control\u2019 tools: these tools provide scores and cut points to distinguish different levels of symptom \ncontrol, validated against health care provider assessment. Many translations are available. These scores may be useful \nfor assessing patient progress; they are commonly used in clinical research, but may be subject to copyright restrictions. \nNumerical asthma control tools are more sensitive to change in symptom cont\u2026[truncated]",
          "score": 0.26832977
        },
        {
          "id": 11246607,
          "source": "gina_asthma_2023",
          "source_id": "gina_asthma_2023:p0043",
          "title": "GINA 2023 Global Strategy for Asthma Management and Prevention \u2013 page 43",
          "text": "42 2. Assessment of asthma \n2 weeks.152 Average PEF continues to increase, and diurnal PEF variability to decrease, for about 3 months. 142,152 \nExcessive variation in PEF suggests suboptimal asthma control, and increases the risk of exacerbations. 153  \nLong-term PEF monitoring is now generally only recommended for patients with severe asthma, or those with \nimpaired perception of airflow limitation.136,154-157 For clinical practice, displaying PEF results on a s\u2026[truncated]",
          "score": 0.098461
        },
        {
          "id": 11246588,
          "source": "gina_asthma_2023",
          "source_id": "gina_asthma_2023:p0024",
          "title": "GINA 2023 Global Strategy for Asthma Management and Prevention \u2013 page 24",
          "text": "1. Definition, description and diagnosis of asthma 23 \nmore severe asthma, some phenotype-guided treatments are available. However, except in patients with severe \nasthma, no strong relationship has been found between specific pathological features and particular clinical patterns or \ntreatment responses. More research is needed to understand the clinical utility of phenotypic classification in asthma.  \nMany clinical phenotypes of asthma have been identified.16-1\u2026[truncated]",
          "score": 0.09818541
        },
        {
          "id": 11246774,
          "source": "gina_asthma_2023",
          "source_id": "gina_asthma_2023:p0210",
          "title": "GINA 2023 Global Strategy for Asthma Management and Prevention \u2013 page 210",
          "text": "References 209 \n73. Schatz M, Zeiger RS, Yang SJ, et al. The relationship of asthma impairment determined by psychometric tools to \nfuture asthma exacerbations. Chest 2012; 141: 66-72. \n74. Stanford RH, Shah MB, D\u2019Souza AO, et al. Short-acting \u03b2-agonist use and its ability to predict future asthma-\nrelated outcomes. Ann Allergy Asthma Immunol 2012; 109: 403-407. \n75. Nwaru BI, Ekstrom M, Hasvold P, et al. Overuse of short-acting beta2-agonists in asthma is associa\u2026[truncated]",
          "score": 0.09800697
        },
        {
          "id": 11244256,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0148",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 148",
          "text": "33. Salabelle C, Ly Sall K, Eroukhmanoff J, et al.\nCOVID-19 pandemic lockdown in young people\nwith type 1 diabetes: positive results of an\nunprecedented challenge for patients through\ntelemedicine and change in use of continuous\nglucose monitoring. Prim Care Diabetes 2021;\n15:884\u2013886\n34. Prabhu Navis J, Leelarathna L, Mubita W,\net al. Impact of COVID-19 lockdown on\ufb02ash and\nreal-time glucose sensor users with type 1\ndiabetes in England. Acta Diabetol 2021;58:\n231\u20132\u2026[truncated]",
          "score": 0.09717292
        },
        {
          "id": 11246572,
          "source": "gina_asthma_2023",
          "source_id": "gina_asthma_2023:p0008",
          "title": "GINA 2023 Global Strategy for Asthma Management and Prevention \u2013 page 8",
          "text": "7 \nPreface \nAsthma is a serious global health problem affecting all age groups. Its prevalence is increasing in many countries, \nespecially among children. Although some countries have seen a decline in hospitalizations and deaths from asthma, \nasthma still imposes an unacceptable burden on health care systems, and on society through loss of productivity in the \nworkplace and, especially for pediatric asthma, disruption to the family. \nThis year, the Global Initia\u2026[truncated]",
          "score": 0.09703509
        }
      ],
      "overlap": {
        "semantic_only": [
          11246565,
          11246566,
          11246570,
          11246580,
          11246581,
          11246767,
          11246809
        ],
        "ts_only": [
          11244256,
          11246588,
          11246602,
          11246607,
          11246646,
          11246745,
          11246774
        ],
        "both": [
          11246572
        ],
        "jaccard": 0.06666666666666667
      },
      "llm": {
        "error": "500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat",
        "model": "eoh-llama:70b"
      },
      "batch_index": 6
    },
    {
      "query": "How do ADA 2024 recommendations prioritize GLP-1 vs SGLT2 in CKD?",
      "top_k": 8,
      "sources_filter": null,
      "embed_model": "BAAI/bge-base-en-v1.5",
      "pilot_slice_source_reference": {
        "rxnorm": "NLM RxNorm drug and ingredient concepts (RxCUI, names, TTYs).",
        "loinc": "LOINC laboratory and clinical observation codes with long names.",
        "hpo": "Human Phenotype Ontology terms (phenotypes, disease manifestations).",
        "snomed": "SNOMED CT clinical concepts (disorders, findings, procedures).",
        "icd10cm": "ICD-10-CM diagnosis codes and official long titles (US clinical modification).",
        "icd11": "WHO ICD-11 foundation mortality and morbidity content mirrored for search.",
        "orphanet": "Orphanet rare disease names, synonyms, and classification text.",
        "chv": "Consumer Health Vocabulary \u2014 lay-language terms linked to clinical concepts (UMLS CHV).",
        "va_guidelines": "VA/DoD clinical practice guideline sections ingested as rag_corpus chunks.",
        "acc_aha_valvular_2020": "2020 ACC/AHA guideline on valvular heart disease (chunked text).",
        "ada_dm_2024": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage).",
        "kdigo_ckd_2021": "KDIGO 2021 clinical practice guideline for chronic kidney disease (CKD).",
        "kdigo_ckd_2024": "KDIGO 2024 CKD evaluation and management guideline excerpts.",
        "kdigo_gn_ln_2021": "KDIGO 2021 guideline for glomerular diseases including lupus nephritis.",
        "kdigo_anemia_ckd_2023": "KDIGO 2023 clinical practice guideline for anemia in CKD.",
        "gold_copd_2023": "GOLD 2023 Global Strategy for Diagnosis, Management, and Prevention of COPD.",
        "gold_copd_2024": "GOLD 2024 COPD strategy document excerpts.",
        "gina_asthma_2023": "GINA 2023 Global Strategy for Asthma Management and Prevention.",
        "cdc_opioid": "CDC opioid prescribing guideline narrative sections (structured plain text).",
        "acr_eular": "Joint ACR/EULAR classification or criteria publications (combined tag).",
        "acr_ild_2023": "ACR guidance on idiopathic inflammatory myopathies with ILD (2023).",
        "acr_ra_2021": "ACR guideline or guidance on rheumatoid arthritis management (2021).",
        "acr_npf_psa_2018": "ACR/NPF joint guideline on psoriasis and psoriatic arthritis (2018).",
        "acr_vf_anca_2021": "ACR/VF guideline on ANCA-associated vasculitis (2021).",
        "acr_reproductive_health_2020": "ACR reproductive health guidance for rheumatic disease (2020).",
        "eular_acr_sle_2019": "EULAR/ACR classification criteria or lupus management collaboration (2019).",
        "eular_ra_2022": "EULAR recommendations for rheumatoid arthritis management (2022).",
        "eular_psa_2020": "EULAR recommendations for psoriatic arthritis pharmacologic therapy (2020).",
        "eular_sle_nephritis_2025": "EULAR recommendations on management of lupus nephritis (2025).",
        "eular_anca_2022": "EULAR recommendations for ANCA-associated vasculitis (2022).",
        "eular_lvv_2018": "EULAR recommendations for large-vessel vasculitis (2018).",
        "eular_axspa_2022": "EULAR recommendations for axial spondyloarthritis (2022).",
        "asas_eular_axspa_2022": "ASAS\u2013EULAR recommendations for axial spondyloarthritis (2022).",
        "diagrules": "Curated diagnostic-rule narrative cards used as RAG chunks.",
        "eoh_canon_v6": "Ethos of Health canon v6 narrative chunks (foundational clinical ethos text).",
        "eoh_2025": "Ethos of Health 2025 corpus excerpts in rag_corpus.",
        "eoh_gold_2025": "Ethos of Health \u00d7 GOLD COPD 2025 cross-reference or summary chunks.",
        "ethos_model": "Short Ethos-of-Health model or meta documents (small row count)."
      },
      "router_plan": {
        "question_type": "OTHER",
        "semantic_query": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage) prioritizes GLP-1 vs SGLT2 in chronic kidney disease (CKD). The ADA 2024 recommendations emphasize the importance of GLP-1 as a first-line treatment for CKD patients. In contrast, SGLT2 inhibitors are considered for patients with more advanced CKD or those who have not responded to GLP-1 therapy.",
        "ts_query": "(GLP-1 OR SGLT2) AND (CKD OR chronic kidney disease)",
        "ts_terms": [
          "GLP-1",
          "SGLT2",
          "CKD"
        ],
        "selected_sources": [
          {
            "source": "ada_dm_2024",
            "priority": 1,
            "why": "American Diabetes Association Standards of Care"
          },
          {
            "source": "kdigo_ckd_2024",
            "priority": 2,
            "why": "KDIGO 2024 CKD evaluation and management guideline excerpts"
          }
        ],
        "selected_modules": [
          {
            "module_id": "M13",
            "priority": 1,
            "why": "Trend & Prognostic Engine"
          },
          {
            "module_id": "M6",
            "priority": 2,
            "why": "Escalation Router / Central Switchboard"
          },
          {
            "module_id": "M12",
            "priority": 3,
            "why": "Symptom Narrative Engine"
          }
        ],
        "notes": "The ADA 2024 recommendations prioritize GLP-1 as a first-line treatment for CKD patients. SGLT2 inhibitors are considered for patients with more advanced CKD or those who have not responded to GLP-1 therapy.",
        "elapsed_sec": 3.655,
        "model": "eoh-llama3.2-source-router"
      },
      "effective_sources": [
        "ada_dm_2024",
        "kdigo_ckd_2024"
      ],
      "embed_device": "cuda",
      "embed_text": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage) prioritizes GLP-1 vs SGLT2 in chronic kidney disease (CKD). The ADA 2024 recommendations emphasize the importance of GLP-1 as a first-line treatment for CKD patients. In contrast, SGLT2 inhibitors are considered for patients with more advanced CKD or those who have not responded to GLP-1 therapy.",
      "embed_sec": 2.2067,
      "db_sec": 0.0505,
      "ts_strategy": "per_term+raw_fallback (3 terms)",
      "ts_terms_used": [
        "GLP-1",
        "SGLT2",
        "CKD"
      ],
      "semantic_hits": [
        {
          "id": 11244308,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0200",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 200",
          "text": "leading to the recommendation that sem-\na g l u t i d ec a nb eu s e da sa n o t h e r\ufb01rst-line\nagent for people with CKD (137,138).\nOther GLP-1 RAs (liraglutide and dulaglu-\ntide) may also have CKD bene\ufb01ts, but no\nother dedicated kidney trials have been\npublished. Similarly, no dedicated kidney\noutcomes studies for the dual GIP and\nGLP-1 RA (tirzepatide) have been pub-\nlished. Dedicated kidney outcomes trials\nin people with CKD and type 2 diabetes\nhave shown that\u2026[truncated]",
          "score": 0.8215612662769133
        },
        {
          "id": 11244359,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0251",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 251",
          "text": "activity (92\u201394). Glucagon-like peptide 1\n(GLP-1) receptor agonists (RAs) have\nalso been shown to improve kidney out-\ncomes (95\u2013100). Kidney effects should\nbe considered when selecting agents\nfor glucose lowering (see Section 9,\n\u201cPharmacologic Approaches to Glycemic\nTreatment\u201d).\nSelection of Glucose-Lowering\nMedications for People With Chronic\nKidney Disease\nFor people with type 2 diabetes and es-\ntablished CKD, special considerations for\nthe selection of glucose-\u2026[truncated]",
          "score": 0.8203032643054823
        },
        {
          "id": 11243209,
          "source": "kdigo_ckd_2024",
          "source_id": "kdigo_ckd_2024:p0106",
          "title": "KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 106",
          "text": "Special considerations\nPediatric considerations. No relevant studies to inform this\nguideline have been completed in children.\n3.9 Glucagon-like peptide-1 receptor agonists\n(GLP-1 RA)\nThe Work Group highlights a key recommendation and practice\npoint from the KDIGO 2022 Clinical Practice Guideline for\nDiabetes Management in Chronic Kidney Disease.23\nRecommendation 3.9.1: In adults with T2D and CKD\nwho have not achieved individualized glycemic\ntargets despite use of\u2026[truncated]",
          "score": 0.8031681893367782
        },
        {
          "id": 11244357,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0249",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 249",
          "text": "Comorbidities,\u201d for further information on\nimmunization).\nPrevention\nThe only proven primary prevention inter-\nventions for CKD in people with diabetes\na r eb l o o dg l u c o s e( A 1 Cg o a lo f7 % )a n d\nblood pressure management. There is no\nevidence that renin-angiotensin-aldosterone\nsystem inhibitors or any other interventions\nprevent the development of CKD in the ab-\nsence of hypertension or albuminuria. Thus,\nthe American Diabetes Association does not\nreco\u2026[truncated]",
          "score": 0.7972538350375806
        },
        {
          "id": 11243203,
          "source": "kdigo_ckd_2024",
          "source_id": "kdigo_ckd_2024:p0100",
          "title": "KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 100",
          "text": "without diabetes who are at very low risk of ketoacidosis). SGLT2i\nalso favorably reduce BP, uric acid levels, measures of\ufb02uid over-\nload, the risk of serious hyperkalemia, and do not increase risk of\nhypoglycemia. The recommendation is consistent with but ex-\npands on Recommendation 1.3.1 from theKDIGO 2022 Clinical\nPractice Guideline for Diabetes Management in Chronic Kid-\nney Diseaseto include people with causes of CKD not related to\ndiabetes.\nKey information\nB\u2026[truncated]",
          "score": 0.7967671868294947
        },
        {
          "id": 11243202,
          "source": "kdigo_ckd_2024",
          "source_id": "kdigo_ckd_2024:p0099",
          "title": "KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 99",
          "text": "eGFR <30 ml/min per 1.73 m2, compared with those who\ncontinue.508,509 In addition, a recent individual patient level\ndata meta-analysis demonstrated a bene\ufb01t in delaying KRT\nin patients with eGFR<30 ml/min per 1.73 m2.510\n3.7 Sodium-glucose cotransporter-2 inhibitors\n(SGLT2i)\nThe Work Group concurs with the KDIGO 2022 Clinical\nPractice Guideline for Diabetes Management in Chronic\nKidney Disease, which stated: \u201cWe recommend treating pa-\ntients with type 2 diabetes \u2026[truncated]",
          "score": 0.7830051650408023
        },
        {
          "id": 11244318,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0210",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 210",
          "text": "diabetes: a meta-analysis. JAMA Cardiol 2021;6:\n148\u2013158\n140. Reyes-Farias CI, Reategui-Diaz M, Romani-\nRomani F, Prokop L. The effect of sodium-glucose\ncotransporter 2 inhibitors in patients with chronic\nkidney disease with or without type 2 diabetes\nmellitus on cardiovascular and renal outcomes: a\nsystematic review and meta-analysis. PLoS One\n2023;18:e0295059\n141. Herrington WG, Staplin N, Wanner C, et al.;\nEmpa-Kidney Collaborative Group. Empagli\ufb02ozin\nin patient\u2026[truncated]",
          "score": 0.782313227653509
        },
        {
          "id": 11244352,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0244",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 244",
          "text": "312. Musso G, Sircana A, Saba F, Cassader M,\nGambino R. Assessing the risk of ketoacidosis due\nto sodium-glucose cotransporter (SGLT)-2 in-\nhibitors in patients with type 1 diabetes: a meta-\nanalysis and meta-regression. PLoS Med 2020;\n17:e1003461\n313. Holt RIG, DeVries JH, Hess-Fischl A, et al.\nThe management of type 1 diabetes in adults. A\nconsensus report by the American Diabetes\nAssociation (ADA) and the European Association\nfor the Study of Diabetes (EASD). D\u2026[truncated]",
          "score": 0.7799455624770134
        }
      ],
      "ts_hits": [
        {
          "id": 11244307,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0199",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 199",
          "text": "with A1C levels 1.5\u20132.0% above their indi-\nvidualized goal. Finally, incorporation\nof high-glycemic-ef \ufb01cacy therapies or\ntherapies for cardiovascular and kidney\ndisease risk reduction (e.g., GLP-1 RAs,\ndual GIP and GLP-1 RA, and SGLT2 inhibi-\ntors) may reduce the need for agents that\nincrease the risks of hypoglycemia and\nweight gain or are less well tolerated.\nThus, treatment intensi\ufb01cation requires\npurposeful selection of medications in\nalignment with multiple \u2026[truncated]",
          "score": 0.9897476
        },
        {
          "id": 11244190,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0082",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 82",
          "text": "Given the high prevalence of at-risk\nMASH ( /C24 12\u201320%) (182\u2013 184,186,189),\nhigher risk of disease progression and\nliver-related mortality (185,204,253), and\nthe lack of pharmacological treatments\nonce cirrhosis is established (254,255),\noptimizing the pharmacological manage-\nment of hyperglycemia and obesity in\npeople with type 2 diabetes and MASH\ncould serve the dual purpose of address-\ning these comorbidities while treating\nthe liver disease (Fig. 4.3). Theref\u2026[truncated]",
          "score": 0.94714487
        },
        {
          "id": 11244302,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0194",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 194",
          "text": "9.16b Combination therapy with\npioglitazone plus a GLP-1 RA can be\nconsidered for the treatment of hy-\nperglycemia in adults with type 2\ndiabetes with biopsy-proven MASH\nor those at high risk of liver\ufb01brosis\n(identi\ufb01ed with noninvasive tests)\ndue to potential bene \ufb01cial effects\non MASH. B\n9.17 Medication plan and medication-\ntaking behavior should be reevalua-\nted at regular intervals (e.g., every\n3\u20136 months) and adjusted as needed\nto incorporate speci\ufb01c factors t\u2026[truncated]",
          "score": 0.7995108
        },
        {
          "id": 11243158,
          "source": "kdigo_ckd_2024",
          "source_id": "kdigo_ckd_2024:p0055",
          "title": "KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 55",
          "text": "and transplantation).56 A public health approach toward CKD\ndetection and treatment could reduce inequities in the burden\nof kidney failure by slowing the rate of progression and the\nrisk of CVD for everyone.\n57\nThe possible harm of early detection of CKD is that the\nnew diagnosis may cause anxiety in some people, particularly\nif the testing is not discussed in advance of the results. Dis-\ncussions around disease detection are common in the primary\ncare setting, a\u2026[truncated]",
          "score": 0.098602496
        },
        {
          "id": 11243193,
          "source": "kdigo_ckd_2024",
          "source_id": "kdigo_ckd_2024:p0090",
          "title": "KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 90",
          "text": "Chapter 3: Delaying CKD progression and managing\nits complications\n3.1 CKD treatment and risk modi\ufb01cation\nPractice Point 3.1.1: Treat people with CKD with a\ncomprehensive treatment strategy to reduce risks of\nprogression of CKD and its associated complications\n(Figure 17).\nRisk factors associated with CKD progression, CVD, and\nother CKD complications are highly interrelated,\n435 and\nhence so is their management. We use the term \u201cCKD\ntreatment and risk modi\ufb01cation\u201d\u2026[truncated]",
          "score": 0.098287635
        },
        {
          "id": 11243157,
          "source": "kdigo_ckd_2024",
          "source_id": "kdigo_ckd_2024:p0054",
          "title": "KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 54",
          "text": "Chapter 1: Evaluation of CKD\n1.1 Detection and evaluation of CKD\nBoth decreased GFR and increased albuminuria or other\nmarkers of kidney damage are often silent and not apparent to\nt h ep e r s o na tr i s ko fC K Do rt h eh e a l t h c a r ep r o v i d e ru n l e s s\nlaboratory tests are performed. The cause of the decreased GFR\nor increased albuminuria may also not be apparent. In the\ndecade since the publication of the previous KDIGO Clinical\nPractice Guideline\u2026[truncated]",
          "score": 0.09800697
        },
        {
          "id": 11244340,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0232",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 232",
          "text": "placebo) was 0.70 [95% CI 0.54\u20130.90],\nconsistent with\ufb01ndings from other SGLT2\ninhibitor cardiovascular outcomes trials.\nGLP-1 Receptor Agonist Trials\nThe Liraglutide Effect and Action in Diabe-\ntes: Evaluation of Cardiovascular Outcome\nResults (LEADER) trial was a randomized,\ndouble-blind trial that assessed the effect\nof liraglutide, a GLP-1 RA, versus placebo\non cardiovascular outcomes in 9,340 peo-\np l ew i t ht y p e2d i a b e t e sa th i g hr i s kf o rc a r \u2026[truncated]",
          "score": 0.09421459
        },
        {
          "id": 11243204,
          "source": "kdigo_ckd_2024",
          "source_id": "kdigo_ckd_2024:p0101",
          "title": "KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 101",
          "text": "acid levels,515 weight/\ufb02uid overload,516 and the risk of serious\nhyperkalemia.517\nHarms. SGLT2i are well tolerated with high levels of\nadherence in the RCTs in CKD. 403,513,514 In the studied\npopulations, any risk of ketoacidosis or lower-limb\namputation resulting from SGLT2i use was substantially\nlower than the potential absolute bene \ufb01ts and generally\nrestricted to people with diabetes. Meta-analysis estimates of\nabsolute bene \ufb01ts and harms for each 1000 people \u2026[truncated]",
          "score": 0.092856124
        }
      ],
      "overlap": {
        "semantic_only": [
          11243202,
          11243203,
          11243209,
          11244308,
          11244318,
          11244352,
          11244357,
          11244359
        ],
        "ts_only": [
          11243157,
          11243158,
          11243193,
          11243204,
          11244190,
          11244302,
          11244307,
          11244340
        ],
        "both": [],
        "jaccard": 0.0
      },
      "llm": {
        "error": "500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat",
        "model": "eoh-llama:70b"
      },
      "batch_index": 7
    },
    {
      "query": "Key treatment principles for lupus nephritis in EULAR/KDIGO guidance",
      "top_k": 8,
      "sources_filter": null,
      "embed_model": "BAAI/bge-base-en-v1.5",
      "pilot_slice_source_reference": {
        "rxnorm": "NLM RxNorm drug and ingredient concepts (RxCUI, names, TTYs).",
        "loinc": "LOINC laboratory and clinical observation codes with long names.",
        "hpo": "Human Phenotype Ontology terms (phenotypes, disease manifestations).",
        "snomed": "SNOMED CT clinical concepts (disorders, findings, procedures).",
        "icd10cm": "ICD-10-CM diagnosis codes and official long titles (US clinical modification).",
        "icd11": "WHO ICD-11 foundation mortality and morbidity content mirrored for search.",
        "orphanet": "Orphanet rare disease names, synonyms, and classification text.",
        "chv": "Consumer Health Vocabulary \u2014 lay-language terms linked to clinical concepts (UMLS CHV).",
        "va_guidelines": "VA/DoD clinical practice guideline sections ingested as rag_corpus chunks.",
        "acc_aha_valvular_2020": "2020 ACC/AHA guideline on valvular heart disease (chunked text).",
        "ada_dm_2024": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage).",
        "kdigo_ckd_2021": "KDIGO 2021 clinical practice guideline for chronic kidney disease (CKD).",
        "kdigo_ckd_2024": "KDIGO 2024 CKD evaluation and management guideline excerpts.",
        "kdigo_gn_ln_2021": "KDIGO 2021 guideline for glomerular diseases including lupus nephritis.",
        "kdigo_anemia_ckd_2023": "KDIGO 2023 clinical practice guideline for anemia in CKD.",
        "gold_copd_2023": "GOLD 2023 Global Strategy for Diagnosis, Management, and Prevention of COPD.",
        "gold_copd_2024": "GOLD 2024 COPD strategy document excerpts.",
        "gina_asthma_2023": "GINA 2023 Global Strategy for Asthma Management and Prevention.",
        "cdc_opioid": "CDC opioid prescribing guideline narrative sections (structured plain text).",
        "acr_eular": "Joint ACR/EULAR classification or criteria publications (combined tag).",
        "acr_ild_2023": "ACR guidance on idiopathic inflammatory myopathies with ILD (2023).",
        "acr_ra_2021": "ACR guideline or guidance on rheumatoid arthritis management (2021).",
        "acr_npf_psa_2018": "ACR/NPF joint guideline on psoriasis and psoriatic arthritis (2018).",
        "acr_vf_anca_2021": "ACR/VF guideline on ANCA-associated vasculitis (2021).",
        "acr_reproductive_health_2020": "ACR reproductive health guidance for rheumatic disease (2020).",
        "eular_acr_sle_2019": "EULAR/ACR classification criteria or lupus management collaboration (2019).",
        "eular_ra_2022": "EULAR recommendations for rheumatoid arthritis management (2022).",
        "eular_psa_2020": "EULAR recommendations for psoriatic arthritis pharmacologic therapy (2020).",
        "eular_sle_nephritis_2025": "EULAR recommendations on management of lupus nephritis (2025).",
        "eular_anca_2022": "EULAR recommendations for ANCA-associated vasculitis (2022).",
        "eular_lvv_2018": "EULAR recommendations for large-vessel vasculitis (2018).",
        "eular_axspa_2022": "EULAR recommendations for axial spondyloarthritis (2022).",
        "asas_eular_axspa_2022": "ASAS\u2013EULAR recommendations for axial spondyloarthritis (2022).",
        "diagrules": "Curated diagnostic-rule narrative cards used as RAG chunks.",
        "eoh_canon_v6": "Ethos of Health canon v6 narrative chunks (foundational clinical ethos text).",
        "eoh_2025": "Ethos of Health 2025 corpus excerpts in rag_corpus.",
        "eoh_gold_2025": "Ethos of Health \u00d7 GOLD COPD 2025 cross-reference or summary chunks.",
        "ethos_model": "Short Ethos-of-Health model or meta documents (small row count)."
      },
      "router_plan": {
        "question_type": "OTHER",
        "semantic_query": "Key treatment principles for lupus nephritis in EULAR/KDIGO guidance are crucial for managing this complex condition. The American College of Rheumatology (ACR) and the European League Against Rheumatism (EULAR) have established guidelines that provide evidence-based recommendations for diagnosis, treatment, and management of lupus nephritis.",
        "ts_query": "(lupus|nephritis|EULAR|KDIGO|treatment|principles|guidelines)",
        "ts_terms": [
          "lupus",
          "nephritis",
          "EULAR",
          "KDIGO",
          "treatment",
          "principles",
          "guidelines"
        ],
        "selected_sources": [
          {
            "source": "kdigo_ckd_2024",
            "priority": 1,
            "why": "KDIGO 2024 CKD evaluation and management guideline excerpts provide key treatment principles for lupus nephritis."
          },
          {
            "source": "eular_sle_nephritis_2025",
            "priority": 2,
            "why": "EULAR recommendations on management of lupus nephritis are an essential resource for clinicians managing this condition."
          },
          {
            "source": "kdigo_ckd_2021",
            "priority": 3,
            "why": "KDIGO 2021 clinical practice guideline for chronic kidney disease includes treatment principles for lupus nephritis."
          }
        ],
        "selected_modules": [
          {
            "module_id": "M13",
            "priority": 1,
            "why": "Trend & Prognostic Engine is essential for answering flare risk over next X days/months or is trajectory improving/worsening and why?"
          },
          {
            "module_id": "M14",
            "priority": 2,
            "why": "Action & Escalation Engine helps decide concrete next steps for both patient and clinician given a forecast."
          },
          {
            "module_id": "M10",
            "priority": 3,
            "why": "Crisis Engine / Critical Escalation is necessary for any question that touches 'is this an emergency / crisis protocol?'"
          }
        ],
        "notes": "These sources and modules provide critical information for managing lupus nephritis.",
        "elapsed_sec": 3.88,
        "model": "eoh-llama3.2-source-router"
      },
      "effective_sources": [
        "kdigo_ckd_2024",
        "eular_sle_nephritis_2025",
        "kdigo_ckd_2021"
      ],
      "embed_device": "cuda",
      "embed_text": "Key treatment principles for lupus nephritis in EULAR/KDIGO guidance are crucial for managing this complex condition. The American College of Rheumatology (ACR) and the European League Against Rheumatism (EULAR) have established guidelines that provide evidence-based recommendations for diagnosis, treatment, and management of lupus nephritis.",
      "embed_sec": 2.1839,
      "db_sec": 0.0373,
      "ts_strategy": "per_term (7 terms)",
      "ts_terms_used": [
        "lupus",
        "nephritis",
        "EULAR",
        "KDIGO",
        "treatment",
        "principles",
        "guidelines"
      ],
      "semantic_hits": [
        {
          "id": 11243562,
          "source": "eular_sle_nephritis_2025",
          "source_id": "eular_sle_nephritis_2025:p0012",
          "title": "EULAR 2025 SLE with kidney involvement (lupus nephritis) recommendations \u2013 page 12",
          "text": "research) as the single most important pillar of treatment. The\nrecent advent of new drugs with kidney protective properties\nover a spectrum of diseases associated with CKD (SGLT2i, min-\neralocorticoid receptor antagonists, endothelin receptor antago-\nnists) has helped to realise that prevention of CKD occurrence\nand progression\u2014the ultimate goal of treatment in LN\u2014is best\nserved by the combination of immunosuppression and kidney\nprotection. This two-arm therapy i\u2026[truncated]",
          "score": 0.8225007759034185
        },
        {
          "id": 11243552,
          "source": "eular_sle_nephritis_2025",
          "source_id": "eular_sle_nephritis_2025:p0002",
          "title": "EULAR 2025 SLE with kidney involvement (lupus nephritis) recommendations \u2013 page 2",
          "text": "23 Division of Rheumatology, Department of Medicine Solna, Karolinska Institutet, Karolinska University Hospital, and Center for\nMolecular Medicine (CMM), Stockholm, Sweden\n24 Faculty of Medicine and Health,\u20acOrebro University,\u20acOrebro, Sweden\n25 Department of Rheumatology, University of Medicine and Pharmacy, Cluj-Napoca, Romania\n26 Complejo Asistencial Universitario de Le/C19on (Rheumatology), Le/C19on, Spain\n27 University of Le/C19on, Le/C19on, Spain\n28 Epidemiol\u2026[truncated]",
          "score": 0.8219057533853348
        },
        {
          "id": 11243551,
          "source": "eular_sle_nephritis_2025",
          "source_id": "eular_sle_nephritis_2025:p0001",
          "title": "EULAR 2025 SLE with kidney involvement (lupus nephritis) recommendations \u2013 page 1",
          "text": "Recommendations\nEULAR recommendations for the management of\nsystemic lupus erythematosus with kidney\ninvolvement: 2025 update\nAntonis Fanouriakis 1,*, Myrto Kostopoulou2, Hans-Joachim Anders3,\nJeanette Andersen4, Martin Aringer5, Michael W. Beresford6,7, Andrea Doria8,\nEleni Frangou9,10,11, Richard Furie12, Dafna D. Gladman13, Frederic Houssiau14,\nAlexandre Karras15, Marios Kouloumas16, Anastasia-Vasiliki Madenidou17,\nAna Malvar18, Smaragdi Marinaki19, Chi Chiu Mo\u2026[truncated]",
          "score": 0.8173930375469274
        },
        {
          "id": 11243561,
          "source": "eular_sle_nephritis_2025",
          "source_id": "eular_sle_nephritis_2025:p0011",
          "title": "EULAR 2025 SLE with kidney involvement (lupus nephritis) recommendations \u2013 page 11",
          "text": "recommendations attempts to summarise the major directions in\na simple, yet not simplistic, way, to facilitate the dissemination\nand implementation of the recommendations in clinical prac-\ntice. These major pillars of management are summarised in the\nFigure. The accompanying text of the recommendations will\nprovide the reader with a more thorough understanding of the\nsupporting data behind each statement. In this regard, no signi\ufb01-\ncant changes have been made rega\u2026[truncated]",
          "score": 0.8154453745218903
        },
        {
          "id": 11243566,
          "source": "eular_sle_nephritis_2025",
          "source_id": "eular_sle_nephritis_2025:p0016",
          "title": "EULAR 2025 SLE with kidney involvement (lupus nephritis) recommendations \u2013 page 16",
          "text": "[101] Serna-Pe~na G, Castillo-de la Garza RJ, Garcia-Arellano G, Zamora-Pineda D,\nMaradiaga-Cece~na M, Alarc/C19on GS, et al. Quality indicators and satisfaction\nwith care in patients with systemic lupus erythematosus. Rheumatol Int\n2023;44:831\u20137. doi:10.1007/s00296-023-05429-9\n.\n[102] Loza E, Carmona L, Woolf A, Dougados M, Boers M, Landew/C19e R, et al.\nImplementation of recommendations in rheumatic and musculoskeletal dis-\neases: considerations for development \u2026[truncated]",
          "score": 0.8093458059235247
        },
        {
          "id": 11243554,
          "source": "eular_sle_nephritis_2025",
          "source_id": "eular_sle_nephritis_2025:p0004",
          "title": "EULAR 2025 SLE with kidney involvement (lupus nephritis) recommendations \u2013 page 4",
          "text": "update, wherein \u2018lupus nephritis\u2019 has been substituted by\n\u2018kidney involvement\u2019, to denote that SLE is a systemic disease\nwith various manifestations that may manifest over time, even\nin cases where nephritis can initially present as an organ-domi-\nnant disease. General management includes non-pharmacologic\nmeasures, including sun protection and smoking cessation, as\nwell as the use of hydroxychloroquine (HCQ) [16]. In addition\nto its multiple bene\ufb01ts in SLE in gen\u2026[truncated]",
          "score": 0.7912426590919551
        },
        {
          "id": 11243553,
          "source": "eular_sle_nephritis_2025",
          "source_id": "eular_sle_nephritis_2025:p0003",
          "title": "EULAR 2025 SLE with kidney involvement (lupus nephritis) recommendations \u2013 page 3",
          "text": "USA [RF], 1 from Canada [DDG], and 1 from Argentina [AM]),\nand 2 from Asia (CCM and YT). All members completed a con-\n\ufb02ict of interest form.\nFollowing the assembly of the Task Force, an outline of the\nproposed methodology, a set of the main research questions,\nand the respective Population, Intervention, Comparison, and\nOutcomes (PICOs) were circulated among the panelists for their\ncomments, edits, and possible additions. This process resulted in\n6 different domai\u2026[truncated]",
          "score": 0.7823661825220367
        },
        {
          "id": 11243555,
          "source": "eular_sle_nephritis_2025",
          "source_id": "eular_sle_nephritis_2025:p0005",
          "title": "EULAR 2025 SLE with kidney involvement (lupus nephritis) recommendations \u2013 page 5",
          "text": "CKD. This is especially pertinent in childhood-onset disease, in\nview of the increased prevalence of kidney involvement and\nits associated severity in this age group [21].\nAs both rheumatologists and nephrologists are involved in\nthe care of these patients, an interdisciplinary care team with\ninput from both disciplines is important to ensure optimal out-\ncomes. Age-, ACR-, and GFR-based charts for the estimated\nrisk for CKD are available and should be part of the\u2026[truncated]",
          "score": 0.7808618080102333
        }
      ],
      "ts_hits": [
        {
          "id": 11243564,
          "source": "eular_sle_nephritis_2025",
          "source_id": "eular_sle_nephritis_2025:p0014",
          "title": "EULAR 2025 SLE with kidney involvement (lupus nephritis) recommendations \u2013 page 14",
          "text": "[24] Carlucci PM, Li J, Fava A, Aringer M, Fanouriakis A, Parodis I, et al. High\nincidence of proliferative and membranous nephritis in SLE patients with\nlow proteinuria in the Accelerating Medicines Partnership. Rheumatology\n(Oxford) 2022;61:4335\u201343. doi:10.1093/rheumatology/keac067\n.\n[25] Wang S, Spielman A, Ginsberg M, Parodis I, Fanouriakis A, Aringer M, et al.\nShort- and long-term progression of kidney involvement in systemic lupus\nerythematosus patients with\u2026[truncated]",
          "score": 0.098602496
        },
        {
          "id": 11243565,
          "source": "eular_sle_nephritis_2025",
          "source_id": "eular_sle_nephritis_2025:p0015",
          "title": "EULAR 2025 SLE with kidney involvement (lupus nephritis) recommendations \u2013 page 15",
          "text": "[61] Zhang H, Liu Z, Zhou M, Liu Z, Chen J, Xing C, et al. Multitarget therapy for\nmaintenance treatment of lupus nephritis. J Am Soc Nephrol 2017;\n28:3671\u20138. doi:10.1681/ASN.2017030263.\n[62] Banos A, Bertsias G. Flares in lupus nephritis: risk factors and strategies for\ntheir prevention. Curr Rheumatol Rep 2023;25:183 \u201391. doi: 10.1007/\ns11926-023-01109-6.\n[63] Zen M, Fuzzi E, Loredo Martinez M, Doria A, Morand E, Houssiau F, et al.\nImmunosuppressive therapy with\u2026[truncated]",
          "score": 0.098238006
        },
        {
          "id": 11243563,
          "source": "eular_sle_nephritis_2025",
          "source_id": "eular_sle_nephritis_2025:p0013",
          "title": "EULAR 2025 SLE with kidney involvement (lupus nephritis) recommendations \u2013 page 13",
          "text": "Writing \u2212 review & editing. Chi Chiu Mok:Writing \u2212 review &\nediting. Gabriella Moroni:Writing \u2212 review & editing. Ioannis\nParodis: Writing \u2212 review & editing. Simona Rednic:Writing\n\u2212 review & editing. Cristiana Sieiro Santos:Writing \u2212 review\n& editing. Carlo Alberto Scire:Methodology. Josef S. Smolen:\nWriting \u2212 review & editing. Farah Tamirou:Writing \u2212 review\n& editing. Yoshiya Tanaka:Writing \u2212 review & editing. Y. K.\nOnno Teng:Writing \u2212 review & editing. Elisabet\u2026[truncated]",
          "score": 0.09652707
        },
        {
          "id": 11243558,
          "source": "eular_sle_nephritis_2025",
          "source_id": "eular_sle_nephritis_2025:p0008",
          "title": "EULAR 2025 SLE with kidney involvement (lupus nephritis) recommendations \u2013 page 8",
          "text": "by 12 months. For paediatric patients, there is no evidence\nto suggest that long-term immune treatment of LN should\ndiffer from the treatment of adults.\n7. In patients with sustained complete renal response, gradual\nwithdrawal of immunosuppressive and/or biologic therapy\nshould be considered after 3 years of therapy following\nresponse, taking into consideration the risk for\ufb02are (2a/B).\nThis recommendation relates to the duration of treatment\nand, accordingly, opti\u2026[truncated]",
          "score": 0.09580905
        },
        {
          "id": 11246340,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0180",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 180",
          "text": "References\n1. Kidney Disease: Improving Global Outcomes CKD Work Group. KDIGO\n2012 clinical practice guideline for the evaluation and management of\nchronic kidney disease.Kidney Int Suppl. 2012;3:S1\u2013S150.\n2. National Kidney Foundation. K/DOQI clinical practice guidelines for\nchronic kidney disease: evaluation, classi\ufb01cation, and strati\ufb01cation. Am\nJ Kidney Dis. 2002;39(suppl 1):S1\u2013S266.\n3. Levey AS, de Jong PE, Coresh J, et al. The de\ufb01nition, classi\ufb01cation, and\npro\u2026[truncated]",
          "score": 0.09471701
        },
        {
          "id": 11243283,
          "source": "kdigo_ckd_2024",
          "source_id": "kdigo_ckd_2024:p0180",
          "title": "KDIGO 2024 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 180",
          "text": "References\n1. Kidney Disease: Improving Global Outcomes CKD Work Group. KDIGO\n2012 clinical practice guideline for the evaluation and management of\nchronic kidney disease.Kidney Int Suppl. 2012;3:S1\u2013S150.\n2. National Kidney Foundation. K/DOQI clinical practice guidelines for\nchronic kidney disease: evaluation, classi\ufb01cation, and strati\ufb01cation. Am\nJ Kidney Dis. 2002;39(suppl 1):S1\u2013S266.\n3. Levey AS, de Jong PE, Coresh J, et al. The de\ufb01nition, classi\ufb01cation, and\npro\u2026[truncated]",
          "score": 0.09471701
        },
        {
          "id": 11243552,
          "source": "eular_sle_nephritis_2025",
          "source_id": "eular_sle_nephritis_2025:p0002",
          "title": "EULAR 2025 SLE with kidney involvement (lupus nephritis) recommendations \u2013 page 2",
          "text": "23 Division of Rheumatology, Department of Medicine Solna, Karolinska Institutet, Karolinska University Hospital, and Center for\nMolecular Medicine (CMM), Stockholm, Sweden\n24 Faculty of Medicine and Health,\u20acOrebro University,\u20acOrebro, Sweden\n25 Department of Rheumatology, University of Medicine and Pharmacy, Cluj-Napoca, Romania\n26 Complejo Asistencial Universitario de Le/C19on (Rheumatology), Le/C19on, Spain\n27 University of Le/C19on, Le/C19on, Spain\n28 Epidemiol\u2026[truncated]",
          "score": 0.09421459
        },
        {
          "id": 11243553,
          "source": "eular_sle_nephritis_2025",
          "source_id": "eular_sle_nephritis_2025:p0003",
          "title": "EULAR 2025 SLE with kidney involvement (lupus nephritis) recommendations \u2013 page 3",
          "text": "USA [RF], 1 from Canada [DDG], and 1 from Argentina [AM]),\nand 2 from Asia (CCM and YT). All members completed a con-\n\ufb02ict of interest form.\nFollowing the assembly of the Task Force, an outline of the\nproposed methodology, a set of the main research questions,\nand the respective Population, Intervention, Comparison, and\nOutcomes (PICOs) were circulated among the panelists for their\ncomments, edits, and possible additions. This process resulted in\n6 different domai\u2026[truncated]",
          "score": 0.09421459
        }
      ],
      "overlap": {
        "semantic_only": [
          11243551,
          11243554,
          11243555,
          11243561,
          11243562,
          11243566
        ],
        "ts_only": [
          11243283,
          11243558,
          11243563,
          11243564,
          11243565,
          11246340
        ],
        "both": [
          11243552,
          11243553
        ],
        "jaccard": 0.14285714285714285
      },
      "llm": {
        "error": "500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat",
        "model": "eoh-llama:70b"
      },
      "batch_index": 8
    },
    {
      "query": "When are nonsteroidal MRAs considered in CKD and diabetes?",
      "top_k": 8,
      "sources_filter": null,
      "embed_model": "BAAI/bge-base-en-v1.5",
      "pilot_slice_source_reference": {
        "rxnorm": "NLM RxNorm drug and ingredient concepts (RxCUI, names, TTYs).",
        "loinc": "LOINC laboratory and clinical observation codes with long names.",
        "hpo": "Human Phenotype Ontology terms (phenotypes, disease manifestations).",
        "snomed": "SNOMED CT clinical concepts (disorders, findings, procedures).",
        "icd10cm": "ICD-10-CM diagnosis codes and official long titles (US clinical modification).",
        "icd11": "WHO ICD-11 foundation mortality and morbidity content mirrored for search.",
        "orphanet": "Orphanet rare disease names, synonyms, and classification text.",
        "chv": "Consumer Health Vocabulary \u2014 lay-language terms linked to clinical concepts (UMLS CHV).",
        "va_guidelines": "VA/DoD clinical practice guideline sections ingested as rag_corpus chunks.",
        "acc_aha_valvular_2020": "2020 ACC/AHA guideline on valvular heart disease (chunked text).",
        "ada_dm_2024": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage).",
        "kdigo_ckd_2021": "KDIGO 2021 clinical practice guideline for chronic kidney disease (CKD).",
        "kdigo_ckd_2024": "KDIGO 2024 CKD evaluation and management guideline excerpts.",
        "kdigo_gn_ln_2021": "KDIGO 2021 guideline for glomerular diseases including lupus nephritis.",
        "kdigo_anemia_ckd_2023": "KDIGO 2023 clinical practice guideline for anemia in CKD.",
        "gold_copd_2023": "GOLD 2023 Global Strategy for Diagnosis, Management, and Prevention of COPD.",
        "gold_copd_2024": "GOLD 2024 COPD strategy document excerpts.",
        "gina_asthma_2023": "GINA 2023 Global Strategy for Asthma Management and Prevention.",
        "cdc_opioid": "CDC opioid prescribing guideline narrative sections (structured plain text).",
        "acr_eular": "Joint ACR/EULAR classification or criteria publications (combined tag).",
        "acr_ild_2023": "ACR guidance on idiopathic inflammatory myopathies with ILD (2023).",
        "acr_ra_2021": "ACR guideline or guidance on rheumatoid arthritis management (2021).",
        "acr_npf_psa_2018": "ACR/NPF joint guideline on psoriasis and psoriatic arthritis (2018).",
        "acr_vf_anca_2021": "ACR/VF guideline on ANCA-associated vasculitis (2021).",
        "acr_reproductive_health_2020": "ACR reproductive health guidance for rheumatic disease (2020).",
        "eular_acr_sle_2019": "EULAR/ACR classification criteria or lupus management collaboration (2019).",
        "eular_ra_2022": "EULAR recommendations for rheumatoid arthritis management (2022).",
        "eular_psa_2020": "EULAR recommendations for psoriatic arthritis pharmacologic therapy (2020).",
        "eular_sle_nephritis_2025": "EULAR recommendations on management of lupus nephritis (2025).",
        "eular_anca_2022": "EULAR recommendations for ANCA-associated vasculitis (2022).",
        "eular_lvv_2018": "EULAR recommendations for large-vessel vasculitis (2018).",
        "eular_axspa_2022": "EULAR recommendations for axial spondyloarthritis (2022).",
        "asas_eular_axspa_2022": "ASAS\u2013EULAR recommendations for axial spondyloarthritis (2022).",
        "diagrules": "Curated diagnostic-rule narrative cards used as RAG chunks.",
        "eoh_canon_v6": "Ethos of Health canon v6 narrative chunks (foundational clinical ethos text).",
        "eoh_2025": "Ethos of Health 2025 corpus excerpts in rag_corpus.",
        "eoh_gold_2025": "Ethos of Health \u00d7 GOLD COPD 2025 cross-reference or summary chunks.",
        "ethos_model": "Short Ethos-of-Health model or meta documents (small row count)."
      },
      "router_plan": {
        "question_type": "D",
        "semantic_query": "Nonsteroidal anti-inflammatory drugs (NSAIDs) are considered in patients with chronic kidney disease (CKD) and diabetes when there is a need to reduce inflammation. The choice of NSAID depends on the patient's renal function, comorbidities, and potential interactions with other medications. In general, NSAIDs are preferred over other anti-inflammatory agents due to their efficacy in reducing pain and inflammation while minimizing the risk of adverse effects.",
        "ts_query": "(nsa OR nonsteroidal anti-inflammatory) AND (ckd OR diabetes)",
        "ts_terms": [
          "CKD",
          "diabetes",
          "NSAID",
          "nonsteroidal anti-inflammatory drug"
        ],
        "selected_sources": [
          {
            "source": "kdigo_ckd_2021",
            "priority": 1,
            "why": "KDIGO 2021 clinical practice guideline for chronic kidney disease"
          },
          {
            "source": "ada_dm_2024",
            "priority": 2,
            "why": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage)"
          },
          {
            "source": "eular_anca_2022",
            "priority": 3,
            "why": "EULAR recommendations for ANCA-associated vasculitis"
          }
        ],
        "selected_modules": [
          {
            "module_id": "M13",
            "priority": 1,
            "why": "Trend & Prognostic Engine"
          },
          {
            "module_id": "M6",
            "priority": 2,
            "why": "Escalation Router / Central Switchboard"
          },
          {
            "module_id": "M12",
            "priority": 3,
            "why": "Symptom Narrative Engine"
          }
        ],
        "notes": "This query requires consideration of the patient's renal function and comorbidities when selecting an NSAID.",
        "elapsed_sec": 3.508,
        "model": "eoh-llama3.2-source-router"
      },
      "effective_sources": [
        "kdigo_ckd_2021",
        "ada_dm_2024",
        "eular_anca_2022"
      ],
      "embed_device": "cuda",
      "embed_text": "Nonsteroidal anti-inflammatory drugs (NSAIDs) are considered in patients with chronic kidney disease (CKD) and diabetes when there is a need to reduce inflammation. The choice of NSAID depends on the patient's renal function, comorbidities, and potential interactions with other medications. In general, NSAIDs are preferred over other anti-inflammatory agents due to their efficacy in reducing pain and inflammation while minimizing the risk of adverse effects.",
      "embed_sec": 2.2176,
      "db_sec": 0.0364,
      "ts_strategy": "per_term (4 terms)",
      "ts_terms_used": [
        "CKD",
        "diabetes",
        "NSAID",
        "nonsteroidal anti-inflammatory drug"
      ],
      "semantic_hits": [
        {
          "id": 11246292,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0132",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 132",
          "text": "Kidney disease can be induced or accelerated by the use of\ncertain over-the-counter (OTC) medications, herbal rem-\nedies, and other dietary supplements. One of the most used\nclass of OTC analgesic medications is NSAIDs. NSAIDs are\nassociated with interstitial nephritis, analgesic nephropathy,\nand hypertension.\n739 Indiscriminate chronic OTC NSAID use\nhas been associated with a higher risks of kidney failure\ncompared with nonuse and should be discouraged. 740\u2013743\nH\u2026[truncated]",
          "score": 0.8034260741648497
        },
        {
          "id": 11246353,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0193",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 193",
          "text": "627. Baker M, Perazella MA. NSAIDs in CKD: are they safe?Am J Kidney Dis.\n2020;76:546\u2013557.\n628. Ralston SH, Capell HA, Sturrock RD. Alcohol and response to treatment\nof gout. Br Med J (Clin Res Ed). 1988;296:1641\u20131642.\n629. Stirpe F, Della Corte E, Bonetti E, et al. Fructose-induced hyperuricaemia.\nLancet. 1970;2:1310\u20131311.\n630. Choi JW, Ford ES, Gao X, et al. Sugar-sweetened soft drinks, diet soft\ndrinks, and serum uric acid level: the Third National Health and\nN\u2026[truncated]",
          "score": 0.7762825026343886
        },
        {
          "id": 11246277,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0117",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 117",
          "text": "Practice Point 3.14.3: For symptomatic treatment of acute\ngout in CKD, low-dose colchicine or intra-articular/oral\nglucocorticoids are preferable to nonsteroidal anti-in\ufb02am-\nmatory drugs (NSAIDs).\nThe American College of Rheumatology recommended that\ncolchicine, NSAIDs, or glucocorticoids are preferred\ufb01rst-line\ntherapies for acute gout treatment based on demonstrated high\nlevels of evidence for ef\ufb01cacy, low cost, and tolerability.\n607\nAdministration early after sy\u2026[truncated]",
          "score": 0.7571084933683003
        },
        {
          "id": 11244356,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0248",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 248",
          "text": "associated with risk of cardiovascular dis-\nease (CVD), CKD progression, and mortal-\nity (6). Therefore, there is an additional\nsubclassi\ufb01cation by level of urine albumin\n(Fig. 11.1). Furthermore, Kidney Disease:\nImproving Global Outcomes (KDIGO) rec-\nommends a more comprehensive CKD\nstaging that incorporates albuminuria at\nall stages of eGFR; this system is more\nclosely associated with risk but is also more\ncomplex (1). Thus, based on the current\nclassi\ufb01cation sy\u2026[truncated]",
          "score": 0.7418651734671012
        },
        {
          "id": 11246304,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0144",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 144",
          "text": "population or people on hemodialysis. For example, sexual\ndysfunction, a very common and one of the most severe\nsymptoms described by people with CKD, is fraught with\nbarriers in terms of research from agreement of de\ufb01nitions,\nthe stigma of sexual dysfunction, acknowledging the\ndistinction between sex and gender, discordance between\nresearch priorities and patient priorities, and understanding\nthat there are variable responses to treatment in people\nwith CKD.\n847 \u2026[truncated]",
          "score": 0.7255456342317533
        },
        {
          "id": 11246291,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0131",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 131",
          "text": "Chapter 4: Medication management and drug\nstewardship in CKD\nMedication management is an important component of the\ncare of people with CKD. Medications can be highly bene\ufb01-\ncial, but some may be toxic, are excreted by the kidney, may\nhave narrow therapeutic windows, or may have no proven\nclear evidence of bene\ufb01t or indication in people with CKD.\nDrug stewardship refers to the effective, safe, and sus-\ntainable use of medications by all staff and physicians,\nencom\u2026[truncated]",
          "score": 0.7201442456073519
        },
        {
          "id": 11244357,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0249",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 249",
          "text": "Comorbidities,\u201d for further information on\nimmunization).\nPrevention\nThe only proven primary prevention inter-\nventions for CKD in people with diabetes\na r eb l o o dg l u c o s e( A 1 Cg o a lo f7 % )a n d\nblood pressure management. There is no\nevidence that renin-angiotensin-aldosterone\nsystem inhibitors or any other interventions\nprevent the development of CKD in the ab-\nsence of hypertension or albuminuria. Thus,\nthe American Diabetes Association does not\nreco\u2026[truncated]",
          "score": 0.7149963718657101
        },
        {
          "id": 11246286,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0126",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 126",
          "text": "thromboembolic events, with an annual rate of 2.9%\ncompared with 0.2% in people without CKD.711\nIncluding GFR into atrial \ufb01brillation risk scores has not\nshown important incremental bene\ufb01t to its introduction (e.g.,\nadding 2 points for CrCl<60 ml/min to CHADS2\u2014 referred\nto as Renal Dysfunction, Congestive Heart Failure, Hyper-\ntension, Age, Diabetes, Stroke/Transient Ischemic Attack\n[R\n2CHADS2])\u2014 improved net reclassi\ufb01cation index but not\nthe C-statistic.710 Howev\u2026[truncated]",
          "score": 0.7125333122889327
        }
      ],
      "ts_hits": [
        {
          "id": 11246355,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0195",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 195",
          "text": "advanced chronic kidney disease]. Kardiologiia. 2020;60:1322 [in\nRussian].\n718. Fox KA, Piccini JP, Wojdyla D, et al. Prevention of stroke and systemic\nembolism with rivaroxaban compared with warfarin in patients with\nnon-valvular atrial \ufb01brillation and moderate renal impairment. Eur\nHeart J. 2011;32:2387\u20132394.\n719. Hijazi Z, Hohnloser SH, Oldgren J, et al. Ef\ufb01cacy and safety of dabigatran\ncompared with warfarin in patients with atrial\ufb01brillation in relation to\nre\u2026[truncated]",
          "score": 0.8464268
        },
        {
          "id": 11246271,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0111",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 111",
          "text": "monitoring, please refer toFigure 21. See Section4.3 for more\ninformation on continuing RASi after hyperkalemia events.\n3.11.2 Potassium exchange agents\nPractice Point 3.11.2.1: Be aware of local availability or\nformulary restrictions with regard to the pharmacologic\nmanagement of nonemergent hyperkalemia.\nThe pharmacologic management of nonemergent hyper-\nkalemia has a number of clinical tools with the increased\nnumber of licensed potassium exchange agents. These\u2026[truncated]",
          "score": 0.75288284
        },
        {
          "id": 11246292,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0132",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 132",
          "text": "Kidney disease can be induced or accelerated by the use of\ncertain over-the-counter (OTC) medications, herbal rem-\nedies, and other dietary supplements. One of the most used\nclass of OTC analgesic medications is NSAIDs. NSAIDs are\nassociated with interstitial nephritis, analgesic nephropathy,\nand hypertension.\n739 Indiscriminate chronic OTC NSAID use\nhas been associated with a higher risks of kidney failure\ncompared with nonuse and should be discouraged. 740\u2013743\nH\u2026[truncated]",
          "score": 0.64423865
        },
        {
          "id": 11244160,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0052",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 52",
          "text": "early childhood diabetes: The Environmental\nDeterminants of Diabetes in the Young (TEDDY).\nDiabetes Care 2015;38:808\u2013813\n54. McKeigue PM, Spiliopoulou A, McGurnaghan\nS, et al. Persistent C-peptide secretion in type 1\ndiabetes and its relationship to the genetic\narchitecture of diabetes. BMC Med 2019;17:165\n55. Sosenko JM, Palmer JP , Rafkin-Mervis L,\net al.; Diabetes Prevention Trial-Type 1 Study\nGroup. Incident dysglycemia and progression to\ntype 1 diabetes among\u2026[truncated]",
          "score": 0.099297166
        },
        {
          "id": 11244414,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0306",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 306",
          "text": "10. Driscoll KA, Volkening LK, Haro H, et al. Are\nchildren with type 1 diabetes safe at school?\nExamining parent perceptions. Pediatr Diabetes\n2015;16:613\u2013620\n11. Cogen F, Rodriguez H, March CA, et al.\nDiabetes care in the school setting: a statement\nof the American Diabetes Association. Diabetes\nCare 2024;47:2050\u20132061\n12. Mehta SN, Volkening LK, Anderson BJ, et al.;\nFamily Management of Childhood Diabetes\nStudy Steering Committee. Dietary behaviors\npredict glycem\u2026[truncated]",
          "score": 0.099254064
        },
        {
          "id": 11244228,
          "source": "ada_dm_2024",
          "source_id": "ada_dm_2024:p0120",
          "title": "ADA Standards of Medical Care in Diabetes \u2014 2024 \u2013 page 120",
          "text": "sleep dif\ufb01culties, referral to sleep special-\nists to address the medical and behavioral\naspects of sleep is recommended, ideally\nin collaboration with the diabetes care\nteam (Fig. 5.2).\nReferences\n1. Young-Hyman D, de Groot M, Hill-Briggs F,\nGonzalez JS, Hood K, Peyrot M. Psychosocial care\nfor people with diabetes: a position statement of\nthe American Diabetes Association. Diabetes\nCare 2016;39:2126\u20132140\n2. Powers MA, Bardsley JK, Cypress M, et al.\nDiabetes self-\u2026[truncated]",
          "score": 0.099235296
        },
        {
          "id": 11246215,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0055",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 55",
          "text": "and transplantation).56 A public health approach toward CKD\ndetection and treatment could reduce inequities in the burden\nof kidney failure by slowing the rate of progression and the\nrisk of CVD for everyone.\n57\nThe possible harm of early detection of CKD is that the\nnew diagnosis may cause anxiety in some people, particularly\nif the testing is not discussed in advance of the results. Dis-\ncussions around disease detection are common in the primary\ncare setting, a\u2026[truncated]",
          "score": 0.098602496
        },
        {
          "id": 11246250,
          "source": "kdigo_ckd_2021",
          "source_id": "kdigo_ckd_2021:p0090",
          "title": "KDIGO 2021 Clinical Practice Guideline for the Evaluation and Management of Chronic Kidney Disease \u2013 page 90",
          "text": "Chapter 3: Delaying CKD progression and managing\nits complications\n3.1 CKD treatment and risk modi\ufb01cation\nPractice Point 3.1.1: Treat people with CKD with a\ncomprehensive treatment strategy to reduce risks of\nprogression of CKD and its associated complications\n(Figure 17).\nRisk factors associated with CKD progression, CVD, and\nother CKD complications are highly interrelated,\n435 and\nhence so is their management. We use the term \u201cCKD\ntreatment and risk modi\ufb01cation\u201d\u2026[truncated]",
          "score": 0.098287635
        }
      ],
      "overlap": {
        "semantic_only": [
          11244356,
          11244357,
          11246277,
          11246286,
          11246291,
          11246304,
          11246353
        ],
        "ts_only": [
          11244160,
          11244228,
          11244414,
          11246215,
          11246250,
          11246271,
          11246355
        ],
        "both": [
          11246292
        ],
        "jaccard": 0.06666666666666667
      },
      "llm": {
        "error": "500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat",
        "model": "eoh-llama:70b"
      },
      "batch_index": 9
    },
    {
      "query": "Summarize opioid prescribing cautions from CDC guidance",
      "top_k": 8,
      "sources_filter": null,
      "embed_model": "BAAI/bge-base-en-v1.5",
      "pilot_slice_source_reference": {
        "rxnorm": "NLM RxNorm drug and ingredient concepts (RxCUI, names, TTYs).",
        "loinc": "LOINC laboratory and clinical observation codes with long names.",
        "hpo": "Human Phenotype Ontology terms (phenotypes, disease manifestations).",
        "snomed": "SNOMED CT clinical concepts (disorders, findings, procedures).",
        "icd10cm": "ICD-10-CM diagnosis codes and official long titles (US clinical modification).",
        "icd11": "WHO ICD-11 foundation mortality and morbidity content mirrored for search.",
        "orphanet": "Orphanet rare disease names, synonyms, and classification text.",
        "chv": "Consumer Health Vocabulary \u2014 lay-language terms linked to clinical concepts (UMLS CHV).",
        "va_guidelines": "VA/DoD clinical practice guideline sections ingested as rag_corpus chunks.",
        "acc_aha_valvular_2020": "2020 ACC/AHA guideline on valvular heart disease (chunked text).",
        "ada_dm_2024": "American Diabetes Association Standards of Care (diabetes mellitus, 2024 vintage).",
        "kdigo_ckd_2021": "KDIGO 2021 clinical practice guideline for chronic kidney disease (CKD).",
        "kdigo_ckd_2024": "KDIGO 2024 CKD evaluation and management guideline excerpts.",
        "kdigo_gn_ln_2021": "KDIGO 2021 guideline for glomerular diseases including lupus nephritis.",
        "kdigo_anemia_ckd_2023": "KDIGO 2023 clinical practice guideline for anemia in CKD.",
        "gold_copd_2023": "GOLD 2023 Global Strategy for Diagnosis, Management, and Prevention of COPD.",
        "gold_copd_2024": "GOLD 2024 COPD strategy document excerpts.",
        "gina_asthma_2023": "GINA 2023 Global Strategy for Asthma Management and Prevention.",
        "cdc_opioid": "CDC opioid prescribing guideline narrative sections (structured plain text).",
        "acr_eular": "Joint ACR/EULAR classification or criteria publications (combined tag).",
        "acr_ild_2023": "ACR guidance on idiopathic inflammatory myopathies with ILD (2023).",
        "acr_ra_2021": "ACR guideline or guidance on rheumatoid arthritis management (2021).",
        "acr_npf_psa_2018": "ACR/NPF joint guideline on psoriasis and psoriatic arthritis (2018).",
        "acr_vf_anca_2021": "ACR/VF guideline on ANCA-associated vasculitis (2021).",
        "acr_reproductive_health_2020": "ACR reproductive health guidance for rheumatic disease (2020).",
        "eular_acr_sle_2019": "EULAR/ACR classification criteria or lupus management collaboration (2019).",
        "eular_ra_2022": "EULAR recommendations for rheumatoid arthritis management (2022).",
        "eular_psa_2020": "EULAR recommendations for psoriatic arthritis pharmacologic therapy (2020).",
        "eular_sle_nephritis_2025": "EULAR recommendations on management of lupus nephritis (2025).",
        "eular_anca_2022": "EULAR recommendations for ANCA-associated vasculitis (2022).",
        "eular_lvv_2018": "EULAR recommendations for large-vessel vasculitis (2018).",
        "eular_axspa_2022": "EULAR recommendations for axial spondyloarthritis (2022).",
        "asas_eular_axspa_2022": "ASAS\u2013EULAR recommendations for axial spondyloarthritis (2022).",
        "diagrules": "Curated diagnostic-rule narrative cards used as RAG chunks.",
        "eoh_canon_v6": "Ethos of Health canon v6 narrative chunks (foundational clinical ethos text).",
        "eoh_2025": "Ethos of Health 2025 corpus excerpts in rag_corpus.",
        "eoh_gold_2025": "Ethos of Health \u00d7 GOLD COPD 2025 cross-reference or summary chunks.",
        "ethos_model": "Short Ethos-of-Health model or meta documents (small row count)."
      },
      "router_plan": {
        "question_type": "C",
        "semantic_query": "Summarize opioid prescribing cautions from CDC guidance. The Centers for Disease Control and Prevention (CDC) provides guidelines for safe opioid prescribing practices to reduce the risk of overdose and addiction. These guidelines emphasize the importance of using the lowest effective dose, monitoring patients closely, and avoiding long-term use.",
        "ts_query": "(opioid|prescribing|caution|CDC|guideline)",
        "ts_terms": [
          "opioid",
          "prescribing",
          "caution",
          "CDC",
          "guideline"
        ],
        "selected_sources": [
          {
            "source": "cdc_opioid",
            "priority": 1,
            "why": "Primary source for CDC opioid prescribing guidelines"
          },
          {
            "source": "ada_dm_2024",
            "priority": 2,
            "why": "Additional guidance on safe opioid use in diabetes management"
          },
          {
            "source": "kdigo_ckd_2021",
            "priority": 3,
            "why": "KDIGO guideline on chronic kidney disease and opioid use"
          }
        ],
        "selected_modules": [
          {
            "module_id": "M13",
            "priority": 1,
            "why": "Trend & Prognostic Engine for flare risk assessment"
          },
          {
            "module_id": "M6",
            "priority": 2,
            "why": "Escalation Router / Central Switchboard for opioid-related alerts"
          }
        ],
        "notes": "These sources provide critical information on safe opioid prescribing practices and guidelines from reputable organizations.",
        "elapsed_sec": 3.199,
        "model": "eoh-llama3.2-source-router"
      },
      "effective_sources": [
        "cdc_opioid",
        "ada_dm_2024",
        "kdigo_ckd_2021"
      ],
      "embed_device": "cuda",
      "embed_text": "Summarize opioid prescribing cautions from CDC guidance. The Centers for Disease Control and Prevention (CDC) provides guidelines for safe opioid prescribing practices to reduce the risk of overdose and addiction. These guidelines emphasize the importance of using the lowest effective dose, monitoring patients closely, and avoiding long-term use.",
      "embed_sec": 2.1729,
      "db_sec": 0.043,
      "ts_strategy": "per_term (5 terms)",
      "ts_terms_used": [
        "opioid",
        "prescribing",
        "caution",
        "CDC",
        "guideline"
      ],
      "semantic_hits": [
        {
          "id": 10477723,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "Guideline Recommendations and Guiding Principles | Overdose Prevention | CDC \u2014 On This Page",
          "text": "2022 Clinical Practice Guideline recommendations Guiding principles for implementing recommendations Determining whether or not to initiate opioids for pain Selecting opioids and determining opioid dosages Deciding duration of initial opioid prescription and conducting follow-up Assessing risk and addressing potential harms of opioid use",
          "score": 0.8667545318603516
        },
        {
          "id": 10477859,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "Guideline Recommendations and Guiding Principles | Overdose Prevention | CDC \u2014 On This Page",
          "text": "2022 Clinical Practice Guideline recommendations Guiding principles for implementing recommendations Determining whether or not to initiate opioids for pain Selecting opioids and determining opioid dosages Deciding duration of initial opioid prescription and conducting follow-up Assessing risk and addressing potential harms of opioid use",
          "score": 0.8667545318603516
        },
        {
          "id": 10484543,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "Guideline Recommendations and Guiding Principles | Overdose Prevention | CDC \u2014 On This Page",
          "text": "2022 Clinical Practice Guideline recommendations Guiding principles for implementing recommendations Determining whether or not to initiate opioids for pain Selecting opioids and determining opioid dosages Deciding duration of initial opioid prescription and conducting follow-up Assessing risk and addressing potential harms of opioid use",
          "score": 0.8667545318603516
        },
        {
          "id": 10477853,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "Guideline Recommendations and Guiding Principles | Overdose Prevention | CDC \u2014 Assessing risk and addressing potential harms of opioid use",
          "text": "Assessing risk and addressing potential harms of opioid use are addressed by recommendations 8, 9, 10, 11, 12.",
          "score": 0.862857512405964
        },
        {
          "id": 10484541,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "Guideline Recommendations and Guiding Principles | Overdose Prevention | CDC \u2014 Assessing risk and addressing potential harms of opioid use",
          "text": "Assessing risk and addressing potential harms of opioid use are addressed by recommendations 8, 9, 10, 11, 12.",
          "score": 0.862857512405964
        },
        {
          "id": 10477717,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "Guideline Recommendations and Guiding Principles | Overdose Prevention | CDC \u2014 Assessing risk and addressing potential harms of opioid use",
          "text": "Assessing risk and addressing potential harms of opioid use are addressed by recommendations 8, 9, 10, 11, 12.",
          "score": 0.862857512405964
        },
        {
          "id": 10477841,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "Guideline Recommendations and Guiding Principles | Overdose Prevention | CDC \u2014 2022 Clinical Practice Guideline recommendations",
          "text": "The 12 recommendations are grouped into four areas of consideration. Determining whether or not to initiate opioids for pain (Recommendations 1, 2) Selecting opioids and determining opioid dosages (Recommendations 3, 4, 5) Deciding duration of initial opioid prescription and conducting follow-up (Recommendations 6, 7) Assessing risk and addressing potential harms of opioid use (Recommendations 8, 9, 10, 11, 12)",
          "score": 0.852546053821325
        },
        {
          "id": 10477705,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "Guideline Recommendations and Guiding Principles | Overdose Prevention | CDC \u2014 2022 Clinical Practice Guideline recommendations",
          "text": "The 12 recommendations are grouped into four areas of consideration. Determining whether or not to initiate opioids for pain (Recommendations 1, 2) Selecting opioids and determining opioid dosages (Recommendations 3, 4, 5) Deciding duration of initial opioid prescription and conducting follow-up (Recommendations 6, 7) Assessing risk and addressing potential harms of opioid use (Recommendations 8, 9, 10, 11, 12)",
          "score": 0.852546053821325
        }
      ],
      "ts_hits": [
        {
          "id": 10477831,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "CDC Clinical Practice Guideline for Prescribing Opioids for Pain \u2014 United States, 2022  | MMWR \u2014 Recommendation 12",
          "text": "Clinicians should offer or arrange treatment with evidence-based medications to treat patients with opioid use disorder. Detoxification on its own, without medications for opioid use disorder, is not recommended for opioid use disorder because of increased risks for resuming drug use, overdose, and overdose death (recommendation category: A; evidence type: 1). Implementation Considerations Although stigma can reduce the willingness of persons with opioid use disor\u2026[truncated]",
          "score": 0.09947363
        },
        {
          "id": 10477695,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "CDC Clinical Practice Guideline for Prescribing Opioids for Pain \u2014 United States, 2022  | MMWR \u2014 Recommendation 12",
          "text": "Clinicians should offer or arrange treatment with evidence-based medications to treat patients with opioid use disorder. Detoxification on its own, without medications for opioid use disorder, is not recommended for opioid use disorder because of increased risks for resuming drug use, overdose, and overdose death (recommendation category: A; evidence type: 1). Implementation Considerations Although stigma can reduce the willingness of persons with opioid use disor\u2026[truncated]",
          "score": 0.09947363
        },
        {
          "id": 10484468,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "CDC Clinical Practice Guideline for Prescribing Opioids for Pain \u2014 United States, 2022  | MMWR \u2014 Recommendation 12",
          "text": "Clinicians should offer or arrange treatment with evidence-based medications to treat patients with opioid use disorder. Detoxification on its own, without medications for opioid use disorder, is not recommended for opioid use disorder because of increased risks for resuming drug use, overdose, and overdose death (recommendation category: A; evidence type: 1). Implementation Considerations Although stigma can reduce the willingness of persons with opioid use disor\u2026[truncated]",
          "score": 0.09947363
        },
        {
          "id": 10477834,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "CDC Clinical Practice Guideline for Prescribing Opioids for Pain \u2014 United States, 2022  | MMWR \u2014 Conclusion and Future Directions",
          "text": "CDC indicated the intent to evaluate and reassess the 2016 CDC Opioid Prescribing Guideline as new evidence became available and determine when sufficient new evidence would prompt an update ( 56 ). CDC funded AHRQ to conduct systematic reviews of the scientific evidence. The following five areas were assessed: 1) noninvasive nonpharmacologic treatments for chronic pain, 2) nonopioid pharmacologic treatments for chronic pain, 3) opioid treatments for chronic pain,\u2026[truncated]",
          "score": 0.09761626
        },
        {
          "id": 10477698,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "CDC Clinical Practice Guideline for Prescribing Opioids for Pain \u2014 United States, 2022  | MMWR \u2014 Conclusion and Future Directions",
          "text": "CDC indicated the intent to evaluate and reassess the 2016 CDC Opioid Prescribing Guideline as new evidence became available and determine when sufficient new evidence would prompt an update ( 56 ). CDC funded AHRQ to conduct systematic reviews of the scientific evidence. The following five areas were assessed: 1) noninvasive nonpharmacologic treatments for chronic pain, 2) nonopioid pharmacologic treatments for chronic pain, 3) opioid treatments for chronic pain,\u2026[truncated]",
          "score": 0.09761626
        },
        {
          "id": 10484522,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "CDC Clinical Practice Guideline for Prescribing Opioids for Pain \u2014 United States, 2022  | MMWR \u2014 Conclusion and Future Directions",
          "text": "CDC indicated the intent to evaluate and reassess the 2016 CDC Opioid Prescribing Guideline as new evidence became available and determine when sufficient new evidence would prompt an update ( 56 ). CDC funded AHRQ to conduct systematic reviews of the scientific evidence. The following five areas were assessed: 1) noninvasive nonpharmacologic treatments for chronic pain, 2) nonopioid pharmacologic treatments for chronic pain, 3) opioid treatments for chronic pain,\u2026[truncated]",
          "score": 0.09761626
        },
        {
          "id": 10477644,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "CDC Clinical Practice Guideline for Prescribing Opioids for Pain \u2014 United States, 2022  | MMWR \u2014 Background",
          "text": "Pain is one of the most common reasons adults seek medical care in the United States ( 1 ). Acute pain, a nearly universal experience, is a physiologic response to noxious stimuli that can become pathologic. Acute pain is usually sudden in onset and time limited (defined in this clinical practice guideline as having a duration of <1 month) and often is caused by injury, trauma, or medical treatments such as surgery ( 2 , 3 ). Unresolved acute pain or subacute pain\u2026[truncated]",
          "score": 0.09751899
        },
        {
          "id": 10477780,
          "source": "cdc_opioid",
          "source_id": null,
          "title": "CDC Clinical Practice Guideline for Prescribing Opioids for Pain \u2014 United States, 2022  | MMWR \u2014 Background",
          "text": "Pain is one of the most common reasons adults seek medical care in the United States ( 1 ). Acute pain, a nearly universal experience, is a physiologic response to noxious stimuli that can become pathologic. Acute pain is usually sudden in onset and time limited (defined in this clinical practice guideline as having a duration of <1 month) and often is caused by injury, trauma, or medical treatments such as surgery ( 2 , 3 ). Unresolved acute pain or subacute pain\u2026[truncated]",
          "score": 0.09751899
        }
      ],
      "overlap": {
        "semantic_only": [
          10477705,
          10477717,
          10477723,
          10477841,
          10477853,
          10477859,
          10484541,
          10484543
        ],
        "ts_only": [
          10477644,
          10477695,
          10477698,
          10477780,
          10477831,
          10477834,
          10484468,
          10484522
        ],
        "both": [],
        "jaccard": 0.0
      },
      "llm": {
        "error": "500 Server Error: Internal Server Error for url: http://127.0.0.1:11434/api/chat",
        "model": "eoh-llama:70b"
      },
      "batch_index": 10
    }
  ]
}💾 Wrote output file: receipts/FORWARD_KNOWLEDGE_GRAPH_RETRIEVAL_HARNESS_BATCH10_ROUTER_70B_20260425.json
🏁 Harness run complete

