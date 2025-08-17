import { parseJournalAnalysis } from '../parseJournalAnalysis';

describe('parseJournalAnalysis', () => {
  test('handles plain text string input', () => {
    const result = parseJournalAnalysis('This is a plain text analysis');
    
    expect(result).toEqual({
      analysis: 'This is a plain text analysis',
      symptoms: [],
      environmental_factors: [],
      life_stressors: [],
      diagnoses: [],
      journalingRecommendation: { promptType: null, suggestedPrompt: null },
      followUpQuestions: [],
      trackingSuggestions: [],
      patternObservations: "",
      timestamp: null
    });
  });

  test('normalizes mixed symptom formats to strings', () => {
    const input = {
      analysis: 'Test analysis',
      symptoms: [
        'headache',
        { symptom: 'joint pain', severity: 5 },
        { name: 'fatigue' },
        { symptom: 'dizziness', severity: 3 },
        { name: 'muscle aches', severity: 7 }
      ]
    };
    
    const result = parseJournalAnalysis(input);
    
    expect(result.symptoms).toEqual([
      'headache',
      'joint pain', 
      'fatigue',
      'dizziness',
      'muscle aches'
    ]);
  });

  test('filters out invalid symptom objects', () => {
    const input = {
      analysis: 'Test analysis',
      symptoms: [
        'valid symptom',
        { symptom: 'valid object' },
        { name: 'another valid' },
        { severity: 5 }, // no name or symptom
        null,
        undefined,
        '',
        { symptom: '', severity: 3 } // empty symptom
      ]
    };
    
    const result = parseJournalAnalysis(input);
    
    expect(result.symptoms).toEqual([
      'valid symptom',
      'valid object',
      'another valid'
    ]);
  });

  test('handles JSON string input', () => {
    const jsonString = JSON.stringify({
      analysis: 'JSON analysis',
      symptoms: ['headache', { symptom: 'fatigue', severity: 8 }]
    });
    
    const result = parseJournalAnalysis(jsonString);
    
    expect(result.analysis).toBe('JSON analysis');
    expect(result.symptoms).toEqual(['headache', 'fatigue']);
  });

  test('handles malformed JSON as plain text', () => {
    const malformedJson = '{ invalid json }';
    
    const result = parseJournalAnalysis(malformedJson);
    
    expect(result.analysis).toBe('{ invalid json }');
    expect(result.symptoms).toEqual([]);
  });

  test('returns null for null/undefined input', () => {
    expect(parseJournalAnalysis(null)).toBeNull();
    expect(parseJournalAnalysis(undefined)).toBeNull();
    expect(parseJournalAnalysis('')).toBeNull();
  });

  test('normalizes diagnoses structure', () => {
    const input = {
      analysis: 'Test',
      diagnoses: [
        { name: 'Migraine', confidence: 0.8 },
        { name: 'Tension Headache', confidence: '0.6' },
        { name: 'Cluster Headache' } // missing confidence
      ]
    };
    
    const result = parseJournalAnalysis(input);
    
    expect(result.diagnoses).toEqual([
      { name: 'Migraine', confidence: 0.8, status: null, staxLevel: null, zone: null, tags: [] },
      { name: 'Tension Headache', confidence: 0.6, status: null, staxLevel: null, zone: null, tags: [] },
      { name: 'Cluster Headache', confidence: null, status: null, staxLevel: null, zone: null, tags: [] }
    ]);
  });
});
