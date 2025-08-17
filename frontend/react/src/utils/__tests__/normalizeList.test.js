import { normalizeStringList } from '../normalizeList';

describe('normalizeStringList', () => {
  test('handles string arrays', () => {
    expect(normalizeStringList(['fatigue','hunger'])).toEqual(['fatigue','hunger']);
  });

  test('handles object symptoms', () => {
    const input = [{ symptom: 'tired', severity: 5 }, { symptom: 'hungry', severity: 5 }];
    expect(normalizeStringList(input)).toEqual(['tired (Severity: 5/10)', 'hungry (Severity: 5/10)']);
  });

  test('handles mixed shapes and JSON string', () => {
    const json = '[{"symptom":"fatigue","severity":7},"thirst",3,true]';
    expect(normalizeStringList(json)).toEqual(['fatigue (Severity: 7/10)', 'thirst', '3', 'true']);
  });

  test('handles null/undefined gracefully', () => {
    expect(normalizeStringList(null)).toEqual([]);
    expect(normalizeStringList(undefined)).toEqual([]);
  });

  test('handles empty arrays', () => {
    expect(normalizeStringList([])).toEqual([]);
  });

  test('handles single string', () => {
    expect(normalizeStringList('single symptom')).toEqual(['single symptom']);
  });

  test('handles numbers and booleans', () => {
    expect(normalizeStringList([1, true, false, 0])).toEqual(['1', 'true', 'false', '0']);
  });

  test('handles objects with name/label/text properties', () => {
    const input = [
      { name: 'test name' },
      { label: 'test label' },
      { text: 'test text' },
      { other: 'fallback' }
    ];
    expect(normalizeStringList(input)).toEqual(['test name', 'test label', 'test text', '{"other":"fallback"}']);
  });

  test('handles severity variations', () => {
    const input = [
      { symptom: 'pain', severity: 8 },
      { symptom: 'fatigue', Severity: 6 },
      { symptom: 'headache' }
    ];
    expect(normalizeStringList(input)).toEqual([
      'pain (Severity: 8/10)',
      'fatigue (Severity: 6/10)', 
      'headache'
    ]);
  });

  test('filters out null/empty items', () => {
    const input = ['valid', null, '', undefined, 'another valid'];
    expect(normalizeStringList(input)).toEqual(['valid', 'another valid']);
  });
});
