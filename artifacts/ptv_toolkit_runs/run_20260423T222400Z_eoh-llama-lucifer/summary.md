# PTV toolkit harness — eoh-llama-lucifer

- Graph: `C:\2OPMD\2ndOpinionMD-MVP\artifacts\forward_kaleb_package_20260423\PTV_REAL_EHR_20260423.json`
- Graph hash: `f159af9f39d05b6b`
- Questions: 10
- Elapsed: 1018.66s

## Aggregate

- Plan emitted:       10/10 (100%)
- Plan route match:   9/10 (90%)
- Expanded query:     3/10
- Primary-tool match: **10/10** (100%)
- Any-tool match:     10/10 (100%)
- Valid evidence ids: 9/10 (90%)
- Keyword-match:      6/10 (60%)

## Per-question

| # | ID | Route exp → obs | Primary exp → obs | Route ✓ | Primary ✓ | Evidence ✓ | Keyword ✓ |
|---|----|------------------|--------------------|---------|-----------|------------|-----------|
| 1 | q01_drug_hydrocodone | `code_lookup` → `code_lookup` | `code_index_lookup` → `code_index_lookup` | ✅ | ✅ | ❌ | ❌ |
| 2 | q02_icd_i10 | `code_lookup` → `code_lookup` | `code_index_lookup` → `code_index_lookup` | ✅ | ✅ | ✅ | ✅ |
| 3 | q03_labs_2016 | `temporal` → `temporal` | `temporal_scan` → `temporal_scan` | ✅ | ✅ | ✅ | ✅ |
| 4 | q04_semantic_back_pain | `semantic_then_bfs` → `semantic_then_bfs` | `semantic_search` → `semantic_search` | ✅ | ✅ | ✅ | ✅ |
| 5 | q05_rxnorm_lookup | `code_lookup` → `code_lookup` | `code_index_lookup` → `code_index_lookup` | ✅ | ✅ | ✅ | ❌ |
| 6 | q06_diag_workup_bfs | `semantic_then_bfs` → `semantic_then_bfs` | `bfs_expand` → `bfs_expand` | ✅ | ✅ | ✅ | ✅ |
| 7 | q07_recent_meds | `temporal` → `temporal` | `temporal_scan` → `temporal_scan` | ✅ | ✅ | ✅ | ✅ |
| 8 | q08_event_types | `orient` → `orient` | `list_event_types` → `list_event_types` | ✅ | ✅ | ✅ | ❌ |
| 9 | q09_free_text_kidney | `semantic_then_bfs` → `semantic_then_bfs` | `semantic_search` → `semantic_search` | ✅ | ✅ | ✅ | ✅ |
| 10 | q10_overview | `orient` → `graph_stats` | `graph_stats` → `graph_stats` | ❌ | ✅ | ✅ | ❌ |

## Traces

### q01_drug_hydrocodone

> List every hydrocodone-acetaminophen administration in this chart in chronological order. Report each event's date and dose.

Tool-call sequence: `['code_index_lookup', 'code_index_lookup', 'code_index_lookup', 'code_index_lookup', 'code_index_lookup', 'semantic_search']`
Reason stopped: `max_turns_reached`  Elapsed: 69.56s

### q02_icd_i10

> How many events in this chart carry the ICD-10 code I10, and when was it first and last recorded?

Tool-call sequence: `['code_index_lookup', 'temporal_scan', 'semantic_search', 'get_event']`
Reason stopped: `final_answer`  Elapsed: 80.82s

**Answer**

The ICD-10 code I10 was first recorded on 2016-03-07 and last recorded on 2016-03-07. It occurred in 4 events.

**Evidence**: `pdf_p0091_e0004`, `pdf_p0006_e005`, `pdf_p0017_e004`, `pdf_p0091_e001`

### q03_labs_2016

> Give me every lab result recorded during 2016 in date order.

Tool-call sequence: `['temporal_scan', 'semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 108.94s

**Answer**

Lab results in 2016 include potassium, creatinine, TSH, LDL, cholesterol, triglyceride, and HDL levels. Additionally, there are diagnoses of M54.5 (lower back pain) and M12.9 (lumbar facet arthropathy). Medications such as hydrocodone-acetaminophen were prescribed.

**Evidence**: `pdf_p0070_e0000`, `pdf_p0167_generic`, `pdf_p0168_generic`, `pdf_p0071_e000`, `pdf_p0069_e000`, `pdf_p0070_e0001`, `pdf_p0158_e000`, `pdf_p0152_e000`

### q04_semantic_back_pain

> What does this patient's chart say about radiating low back pain?

Tool-call sequence: `['semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 77.7s

**Answer**

The patient has a history of chronic low back pain, confirmed by multiple diagnoses and treatments.

**Evidence**: `pdf_p0091_e0002`, `pdf_p0096_e0005`, `pdf_p0078_e0001`

### q05_rxnorm_lookup

> Is RxNorm 857002 present in this graph? If so, how many events use it?

Tool-call sequence: `['code_index_lookup', 'semantic_search', 'bfs_expand', 'get_event']`
Reason stopped: `final_answer`  Elapsed: 85.1s

**Answer**

The patient has a history of kidney trouble and was prescribed hydrocodone-acetaminophen for pain management. The most recent vital signs recorded on 2016-03-16 show blood pressure at 148/95 mmHg, pulse at 60 beats per minute, weight at 101.6 kg (223 lb), and body mass index at 29.54 kg/m². The patient has also been diagnosed with hypertension (HTN) and hyperlipidemia.

**Evidence**: `pdf_p0103_e0001`, `pdf_p0060_e0001`, `pdf_p0016_e0003`

### q06_diag_workup_bfs

> For the chronic low back pain diagnosis in this chart, what other events happen at the same encounter or are part of its workup?

Tool-call sequence: `['semantic_search', 'bfs_expand', 'list_event_types']`
Reason stopped: `final_answer`  Elapsed: 94.21s

**Answer**

Events related to chronic low back pain diagnosis include: CHRONIC LOW BACK PAIN (primary) [M54.5, G89.29], HYPERLIPIDEMIA [E78.5], HTN [I10], ATRIAL FIBRILLATION, PAROXYSMAL [I48.0], and REACTIVE AIRWAY DISEASE [Z71.89].

**Evidence**: `pdf_p0091_e0002`, `pdf_p0098_generic`

### q07_recent_meds

> Show me every medication event from 2016 in chronological order.

Tool-call sequence: `['temporal_scan', 'semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 69.94s

**Answer**

The patient was prescribed Norco in February 2016. The medication was requested for back pain. A diagnosis of radiculopathy (M54.5) was also made on the same day.

**Evidence**: `pdf_p0076_e0001`, `pdf_p0052_e0000`

### q08_event_types

> What event_type values exist in this graph and how many events of each?

Tool-call sequence: `['list_event_types', 'graph_stats', 'code_index_lookup', 'semantic_search', 'semantic_search']`
Reason stopped: `final_answer`  Elapsed: 117.11s

**Answer**

The patient has a history of kidney trouble and weakness in the legs.

**Evidence**: `pdf_p0017_e0006`, `pdf_p0124_e0000`

### q09_free_text_kidney

> Is there any sign of kidney trouble in this chart?

Tool-call sequence: `['semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 173.93s

**Answer**

There is evidence of kidney trouble in this chart.

**Evidence**: `pdf_p0103_e0001`, `pdf_p0104_generic`

### q10_overview

> Give me a one-paragraph orientation: how many events, what types, what date range?

Tool-call sequence: `['graph_stats', 'list_event_types', 'code_index_lookup', 'semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 141.25s

**Answer**

The patient has been prescribed hydrocodone-acetaminophen for pain, and has received several vaccinations, including PCV13 and PPSV23.

**Evidence**: `pdf_p0012_e0011`, `pdf_p0012_e0006`, `pdf_p0013_e0005`, `pdf_p0013_e0007`, `pdf_p0012_e0000`, `pdf_p0012_e0001`, `pdf_p0012_e0002`, `pdf_p0012_e0003`, `pdf_p0012_e0004`
