## Fix Backend Symptom Storage to Use AI-Extracted Symptoms

This PR addresses the core issue where journal entries were storing raw journal text as symptoms instead of the properly extracted individual symptoms from AI analysis.

### 🐛 **Problem Fixed**

**Root Cause**: The backend was storing raw journal text in the `symptoms` field while AI-extracted structured symptoms were only stored in `ai_analysis.symptoms`, causing inconsistent data storage and display issues.

**Data Flow Issue**:
1. Frontend sends entire journal text as single symptom entry
2. Backend stores raw text in `symptoms` field  
3. AI analysis correctly extracts individual symptoms into `ai_analysis.symptoms`
4. Database ends up with both raw text AND structured symptoms in different fields
5. Display components had to choose between inconsistent data sources

### 🔧 **Changes Made**

**Enhanced Journal Entry Creation** - Updated `server/api/journal.py`:

1. **Symptom Replacement Logic**: After AI analysis completes, replace raw symptoms with AI-extracted structured symptoms before database storage
2. **Data Structure Conversion**: Convert AI-extracted string symptoms to proper `SymptomEntry` format with default severity
3. **Backward Compatibility**: Handle both string and object symptom formats from AI analysis
4. **Enhanced Logging**: Added detailed logging to track symptom replacement process

### ✅ **Result**

**Before**:
```json
{
  "symptoms": [{"symptom": "I feel dizzy when I move too fast. Work has been really stressful, and I keep forgetting things.", "severity": 5}],
  "ai_analysis": {
    "symptoms": ["Dizziness when moving too fast", "Forgetting things", "Work-related stress"]
  }
}
```

**After**:
```json
{
  "symptoms": [
    {"symptom": "Dizziness when moving too fast", "severity": 5},
    {"symptom": "Forgetting things", "severity": 5}, 
    {"symptom": "Work-related stress", "severity": 5}
  ],
  "ai_analysis": {
    "symptoms": ["Dizziness when moving too fast", "Forgetting things", "Work-related stress"]
  }
}
```

### 🔍 **Technical Implementation**

The fix implements symptom replacement logic after AI analysis:

```python
# Replace raw symptoms with AI-extracted structured symptoms
if "symptoms" in ai_analysis and ai_analysis["symptoms"]:
    structured_symptoms = []
    for symptom in ai_analysis["symptoms"]:
        if isinstance(symptom, str):
            structured_symptoms.append({
                "symptom": symptom,
                "severity": 5  # Default severity for AI-extracted symptoms
            })
        elif isinstance(symptom, dict) and "symptom" in symptom:
            structured_symptoms.append(symptom)
    
    if structured_symptoms:
        journal_entry_dict["symptoms"] = structured_symptoms
```

### 📊 **Benefits**

1. **Data Consistency**: All journal entries now store structured symptoms consistently
2. **Improved Display**: Frontend components no longer need complex fallback logic
3. **Better Analytics**: Structured symptom data enables better pattern analysis
4. **Backward Compatibility**: Existing display logic continues to work
5. **Enhanced Debugging**: Detailed logging for symptom replacement process

### 🧪 **Testing Strategy**

- **Database Verification**: Confirm symptoms field contains individual symptom objects
- **Display Testing**: Verify PDF generation and UI components show structured symptoms
- **API Testing**: Test journal entry creation with various symptom formats
- **Backward Compatibility**: Ensure existing entries continue to display correctly

### 🔄 **Migration Notes**

- **Existing Data**: Previous journal entries with raw symptoms will continue to work via fallback logic in display components
- **New Entries**: All new journal entries will store properly structured symptoms
- **No Breaking Changes**: Frontend components already handle both data formats

---

**Link to Devin run**: https://app.devin.ai/sessions/c79c3d8cfafb47508b8c0f9d25e3753b
**Requested by**: dylan@2ndopinionmd.ai

This fix ensures that the symptom storage issue is resolved at the source, providing consistent structured data for all journal entries going forward.
