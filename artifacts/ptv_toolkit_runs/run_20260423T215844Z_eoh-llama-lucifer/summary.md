# PTV toolkit harness — eoh-llama-lucifer

- Graph: `C:\2OPMD\2ndOpinionMD-MVP\artifacts\forward_kaleb_package_20260423\PTV_REAL_EHR_20260423.json`
- Graph hash: `f159af9f39d05b6b`
- Questions: 1
- Elapsed: 41.09s

## Aggregate

- Primary-tool match: **1/1** (100%)
- Any-tool match:     1/1 (100%)
- Valid evidence ids: 1/1 (100%)
- Keyword-match:      0/1 (0%)

## Per-question

| # | ID | Expected | Agent primary | Primary ✓ | Evidence ✓ | Keyword ✓ |
|---|----|----------|---------------|-----------|------------|-----------|
| 1 | q10_overview | `graph_stats` | `graph_stats` | ✅ | ✅ | ❌ |

## Traces

### q10_overview

> Give me a one-paragraph orientation: how many events, what types, what date range?

Tool-call sequence: `['graph_stats', 'list_event_types', 'code_index_lookup']`
Reason stopped: `final_answer`  Elapsed: 41.09s

**Answer**

Hydrocodone-acetaminophen was prescribed on the following dates: 2016-02-11, 2016-02-22, 2016-02-26, 2016-03-02, 2016-03-07, and 2016-03-16.

**Evidence**: `pdf_p0070_e0001`, `pdf_p0071_e0000`, `pdf_p0076_e0001`, `pdf_p0078_e0000`, `pdf_p0079_e0000`, `pdf_p0086_e0000`, `pdf_p0087_e0000`, `pdf_p0096_e0001`, `pdf_p0096_e0003`, `pdf_p0100_e0001`
