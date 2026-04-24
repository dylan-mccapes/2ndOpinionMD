# PTV toolkit harness — eoh-llama-lucifer

- Graph: `C:\2OPMD\2ndOpinionMD-MVP\artifacts\forward_kaleb_package_20260423\PTV_REAL_EHR_20260423.json`
- Graph hash: `f159af9f39d05b6b`
- Questions: 10
- Elapsed: 426.15s

## Aggregate

- Primary-tool match: **10/10** (100%)
- Any-tool match:     10/10 (100%)
- Valid evidence ids: 9/10 (90%)
- Keyword-match:      9/10 (90%)

## Per-question

| # | ID | Expected | Agent primary | Primary ✓ | Evidence ✓ | Keyword ✓ |
|---|----|----------|---------------|-----------|------------|-----------|
| 1 | q01_drug_hydrocodone | `code_index_lookup` | `code_index_lookup` | ✅ | ✅ | ✅ |
| 2 | q02_icd_i10 | `code_index_lookup` | `code_index_lookup` | ✅ | ✅ | ✅ |
| 3 | q03_labs_2016 | `temporal_scan` | `temporal_scan` | ✅ | ✅ | ✅ |
| 4 | q04_semantic_back_pain | `semantic_search` | `semantic_search` | ✅ | ✅ | ✅ |
| 5 | q05_rxnorm_lookup | `code_index_lookup` | `code_index_lookup` | ✅ | ✅ | ✅ |
| 6 | q06_diag_workup_bfs | `bfs_expand` | `bfs_expand` | ✅ | ❌ | ✅ |
| 7 | q07_recent_meds | `temporal_scan` | `temporal_scan` | ✅ | ✅ | ✅ |
| 8 | q08_event_types | `list_event_types` | `list_event_types` | ✅ | ✅ | ✅ |
| 9 | q09_free_text_kidney | `semantic_search` | `semantic_search` | ✅ | ✅ | ✅ |
| 10 | q10_overview | `graph_stats` | `graph_stats` | ✅ | ✅ | ❌ |

## Traces

### q01_drug_hydrocodone

> List every hydrocodone-acetaminophen administration in this chart in chronological order. Report each event's date and dose.

Tool-call sequence: `['code_index_lookup', 'temporal_scan', 'get_event']`
Reason stopped: `final_answer`  Elapsed: 49.27s

**Answer**

Hydrocodone-acetaminophen was administered on the following dates with the specified dose:

* 2016-02-11: 5-325 mg Oral Tab (discontinued)
* 2016-03-07: 5-325 mg Oral Tab

**Evidence**: `pdf_p0070_e0001`, `pdf_p0096_e0003`

### q02_icd_i10

> How many events in this chart carry the ICD-10 code I10, and when was it first and last recorded?

Tool-call sequence: `['code_index_lookup', 'code_index_lookup']`
Reason stopped: `final_answer`  Elapsed: 25.86s

**Answer**

4 events carry the ICD-10 code I10. The first recorded instance was on 2016-03-07 and the last recorded instance was also on 2016-03-07.

**Evidence**: `pdf_p0091_e001`, `pdf_p0091_e0004`, `pdf_p0006_e005`, `pdf_p0017_e004`

### q03_labs_2016

> Give me every lab result recorded during 2016 in date order.

Tool-call sequence: `['temporal_scan', 'get_event']`
Reason stopped: `final_answer`  Elapsed: 44.17s

**Answer**

The lab results recorded during 2016 in date order are: pdf_p0067_e0000, pdf_p0070_e0000, pdf_p0076_e0000, pdf_p0108_generic, pdf_p0137_generic, pdf_p0166_generic, pdf_p0167_generic, pdf_p0168_generic, pdf_p0169_generic.

**Evidence**: `pdf_p0067_e0000`, `pdf_p0070_e0000`, `pdf_p0076_e0000`, `pdf_p0108_generic`, `pdf_p0137_generic`, `pdf_p0166_generic`, `pdf_p0167_generic`, `pdf_p0168_generic`, `pdf_p0169_generic`

### q04_semantic_back_pain

> What does this patient's chart say about radiating low back pain?

Tool-call sequence: `['semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 52.9s

**Answer**

The patient has a history of chronic low back pain, with several diagnoses and treatments related to this condition. The patient was prescribed hydrocodone-acetaminophen for pain management.

**Evidence**: `pdf_p0005_e002`, `pdf_p0078_e0001`

### q05_rxnorm_lookup

> Is RxNorm 857002 present in this graph? If so, how many events use it?

Tool-call sequence: `['code_index_lookup']`
Reason stopped: `final_answer`  Elapsed: 30.44s

**Answer**

RxNorm 857002 is present in the graph, used in 16 events.

**Evidence**: `pdf_p0070_e0001`, `pdf_p0071_e0000`, `pdf_p0076_e0001`, `pdf_p0078_e0000`, `pdf_p0079_e0000`, `pdf_p0086_e0000`, `pdf_p0087_e0000`, `pdf_p0096_e0001`, `pdf_p0096_e0003`, `pdf_p0100_e0001`, `pdf_p0101_e0000`, `pdf_p0116_e0000`

### q06_diag_workup_bfs

> For the chronic low back pain diagnosis in this chart, what other events happen at the same encounter or are part of its workup?

Tool-call sequence: `['bfs_expand', 'bfs_expand', 'get_event']`
Reason stopped: `final_answer`  Elapsed: 31.21s

**Answer**

No additional events found related to the chronic low back pain diagnosis at the same encounter or as part of its workup.

**Evidence**: `pdf_p0001_e001`

### q07_recent_meds

> Show me every medication event from 2016 in chronological order.

Tool-call sequence: `['temporal_scan', 'get_event']`
Reason stopped: `final_answer`  Elapsed: 79.63s

**Answer**

The patient was taking hydrocodone-acetaminophen 5-325 mg Oral Tab, which was discontinued on February 11, 2016. This medication was also mentioned in events pdf_p0078_e0000, pdf_p0079_e0000, pdf_p0096_e0002, and pdf_p0100_e0001.

**Evidence**: `pdf_p0070_e0001`, `pdf_p0078_e0000`, `pdf_p0079_e0000`, `pdf_p0096_e0002`, `pdf_p0100_e0001`

### q08_event_types

> What event_type values exist in this graph and how many events of each?

Tool-call sequence: `['list_event_types', 'code_index_lookup', 'code_index_lookup', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 37.59s

**Answer**

The patient was prescribed hydrocodone-acetaminophen on February 11, 2016. The diagnosis of M54.5 was made on the same day.

**Evidence**: `pdf_p0070_e0001`, `pdf_p0071_e000`, `pdf_p0069_e000`

### q09_free_text_kidney

> Is there any sign of kidney trouble in this chart?

Tool-call sequence: `['semantic_search', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 25.72s

**Answer**

There is a sign of kidney trouble in this chart.

**Evidence**: `pdf_p0017_e0006`, `pdf_p0017_e012`

### q10_overview

> Give me a one-paragraph orientation: how many events, what types, what date range?

Tool-call sequence: `['graph_stats', 'list_event_types', 'code_index_lookup', 'bfs_expand']`
Reason stopped: `final_answer`  Elapsed: 49.35s

**Answer**

The patient was prescribed hydrocodone-acetaminophen (NORCO) for pain, but it was discontinued on March 7, 2016. Ibuprofen 800 mg Oral Tab was also prescribed and taken.

**Evidence**: `pdf_p0070_e0001`, `pdf_p0078_e0000`, `pdf_p0096_e0002`
