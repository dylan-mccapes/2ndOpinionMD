# PTV toolkit harness — eoh-llama-lucifer

- Graph: `C:\2OPMD\2ndOpinionMD-MVP\artifacts\forward_kaleb_package_20260423\PTV_REAL_EHR_20260423.json`
- Graph hash: `f159af9f39d05b6b`
- Questions: 10
- Elapsed: 932.17s

## Aggregate

- Plan emitted:       10/10 (100%)
- Plan route match:   8/10 (80%)
- Expanded query:     3/10
- Primary-tool match: **10/10** (100%)
- Any-tool match:     10/10 (100%)
- Valid evidence ids: 9/10 (90%)
- Keyword-match:      7/10 (70%)

## Per-question

| # | ID | Route exp → obs | Primary exp → obs | Route ✓ | Primary ✓ | Evidence ✓ | Keyword ✓ |
|---|----|------------------|--------------------|---------|-----------|------------|-----------|
| 1 | q01_drug_hydrocodone | `code_lookup` → `code_lookup` | `code_index_lookup` → `code_index_lookup` | ✅ | ✅ | ✅ | ✅ |
| 2 | q02_icd_i10 | `code_lookup` → `code_lookup` | `code_index_lookup` → `code_index_lookup` | ✅ | ✅ | ✅ | ✅ |
| 3 | q03_labs_2016 | `temporal` → `temporal` | `temporal_scan` → `temporal_scan` | ✅ | ✅ | ✅ | ✅ |
| 4 | q04_semantic_back_pain | `semantic_then_bfs` → `semantic_then_bfs` | `semantic_search` → `semantic_search` | ✅ | ✅ | ✅ | ✅ |
| 5 | q05_rxnorm_lookup | `code_lookup` → `code_lookup` | `code_index_lookup` → `code_index_lookup` | ✅ | ✅ | ❌ | ❌ |
| 6 | q06_diag_workup_bfs | `semantic_then_bfs` → `semantic_then_bfs` | `bfs_expand` → `bfs_expand` | ✅ | ✅ | ✅ | ✅ |
| 7 | q07_recent_meds | `temporal` → `temporal` | `temporal_scan` → `temporal_scan` | ✅ | ✅ | ✅ | ✅ |
| 8 | q08_event_types | `orient` → `list_event_types` | `list_event_types` → `list_event_types` | ❌ | ✅ | ✅ | ❌ |
| 9 | q09_free_text_kidney | `semantic_then_bfs` → `semantic_then_bfs` | `semantic_search` → `semantic_search` | ✅ | ✅ | ✅ | ✅ |
| 10 | q10_overview | `orient` → `graph_stats` | `graph_stats` → `graph_stats` | ❌ | ✅ | ✅ | ❌ |

## Traces

### q01_drug_hydrocodone

> List every hydrocodone-acetaminophen administration in this chart in chronological order. Report each event's date and dose.

Tool-call sequence: `['code_index_lookup', 'semantic_search', 'bfs_expand', 'get_event']`
Reason stopped: `final_answer`  Elapsed: 116.87s

**Answer**

The patient was administered hydrocodone-acetaminophen 5-325 mg Oral Tab on the following dates: 2016-02-11, 2016-02-22, 2016-02-26, 2016-03-07. The dose and route of administration varied across these events.

**Evidence**: `pdf_p0070_e0001`, `pdf_p0078_e0000`, `pdf_p0096_e0002`, `pdf_p0096_e0003`

### q02_icd_i10

> How many events in this chart carry the ICD-10 code I10, and when was it first and last recorded?

Tool-call sequence: `['code_index_lookup', 'get_event', 'semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 100.06s

**Answer**

The ICD-10 code I10 was first recorded on 2016-03-07 and last recorded on unknown. There are a total of 4 events with this code.

**Evidence**: `pdf_p0091_e001`, `pdf_p0006_e005`, `pdf_p0017_e004`, `pdf_p0091_e0004`

### q03_labs_2016

> Give me every lab result recorded during 2016 in date order.

Tool-call sequence: `['temporal_scan', 'semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 112.36s

**Answer**

Lab results from February 22, 2016: POTASSIUM 4.0, CREATININE 1.04, TSH 1.13, LDL CALCULATED 124, CHOLESTEROL 226, TRIGLYCERIDE 196, HDL 63. Also, diagnosis of M54.5 (lower back pain) on the same day.

**Evidence**: `pdf_p0076_e0000`, `pdf_p0078_e000`, `pdf_p0075_e000`

### q04_semantic_back_pain

> What does this patient's chart say about radiating low back pain?

Tool-call sequence: `['semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 180.5s

**Answer**

The patient has a history of chronic low back pain, with multiple diagnoses and treatments mentioned in their chart.

**Evidence**: `pdf_p0091_e0002`, `pdf_p0098_generic`

### q05_rxnorm_lookup

> Is RxNorm 857002 present in this graph? If so, how many events use it?

Tool-call sequence: `['code_index_lookup']`
Reason stopped: `max_turns_reached`  Elapsed: 58.54s

### q06_diag_workup_bfs

> For the chronic low back pain diagnosis in this chart, what other events happen at the same encounter or are part of its workup?

Tool-call sequence: `['semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 79.43s

**Answer**

Events related to chronic low back pain diagnosis include hyperlipidemia, hypertension, atrial fibrillation, and reactive airway disease.

**Evidence**: `pdf_p0091_e0002`, `pdf_p0098_generic`, `pdf_p0091_e001`, `pdf_p0091_e002`, `pdf_p0091_e003`, `pdf_p0091_e004`, `pdf_p0091_e005`

### q07_recent_meds

> Show me every medication event from 2016 in chronological order.

Tool-call sequence: `['temporal_scan', 'semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 61.87s

**Answer**

The patient was prescribed Norco 5-325 mg orally every 4 to 6 hours as needed for back pain. The medication was ordered by Dr. Wiltse on March 16, 2016. Additionally, the patient's vital signs were recorded on the same day.

**Evidence**: `pdf_p0100_e0001`, `pdf_p0103_e000`, `pdf_p0106_generic`

### q08_event_types

> What event_type values exist in this graph and how many events of each?

Tool-call sequence: `['list_event_types', 'graph_stats', 'code_index_lookup', 'semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 83.16s

**Answer**

The patient has been prescribed hydrocodone-acetaminophen for pain, and has received various vaccinations including COVID-19 mRNA LNP-S, PF (Moderna) vaccine. There is no evidence of kidney trouble or back pain radiating.

**Evidence**: `pdf_p0014_e0003`, `pdf_p0012_e0000`, `pdf_p0012_e0001`, `pdf_p0012_e0002`, `pdf_p0012_e0003`, `pdf_p0012_e0004`, `pdf_p0012_e0005`

### q09_free_text_kidney

> Is there any sign of kidney trouble in this chart?

Tool-call sequence: `['semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 66.23s

**Answer**

There is evidence of kidney trouble in this chart.

**Evidence**: `pdf_p0103_e0001`, `pdf_p0104_generic`

### q10_overview

> Give me a one-paragraph orientation: how many events, what types, what date range?

Tool-call sequence: `['graph_stats', 'list_event_types', 'code_index_lookup', 'semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 73.12s

**Answer**

The patient has a history of kidney trouble and was prescribed hydrocodone-acetaminophen for back pain. The medication was discontinued on 2016-02-11, but the patient continued to experience back pain and had to resort to taking Norco for relief by 2025-12-05.

**Evidence**: `pdf_p0070_e0001`, `pdf_p0071_e0000`, `pdf_p0069_e000`, `pdf_p0073_generic`
