export function normalizeStringList(value) {
  if (!value) return [];
  if (typeof value === 'string') {
    const trimmed = value.trim();
    if ((trimmed.startsWith('[') && trimmed.endsWith(']')) || (trimmed.startsWith('{') && trimmed.endsWith('}'))) {
      try { return normalizeStringList(JSON.parse(trimmed)); } catch { /* fall through */ }
    }
    return [trimmed];
  }
  if (!Array.isArray(value)) return [String(value)];

  return value.map((item) => {
    if (item == null) return null;
    if (typeof item === 'string') return item.trim();
    if (typeof item === 'number' || typeof item === 'boolean') return String(item);

    if (typeof item === 'object') {
      if ('symptom' in item) {
        const sev = (item.severity ?? item.Severity ?? '').toString();
        return sev ? `${item.symptom} (Severity: ${sev}/10)` : String(item.symptom);
      }
      if ('name' in item) return String(item.name);
      if ('label' in item) return String(item.label);
      if ('text' in item) return String(item.text);

      try { return JSON.stringify(item); } catch { return '[object]'; }
    }
    return String(item);
  }).filter(Boolean);
}
