export function normalizeStringList(value) {
  if (!value) return [];
  if (typeof value === 'string') {
    const s = value.trim();
    if ((s.startsWith('[') && s.endsWith(']')) || (s.startsWith('{') && s.endsWith('}'))) {
      try { return normalizeStringList(JSON.parse(s)); } catch {}
    }
    return s ? [s] : [];
  }
  if (!Array.isArray(value)) return [];

  return value.map((item) => {
    if (item == null) return null;
    if (typeof item === 'string') return item.trim();
    if (typeof item === 'number' || typeof item === 'boolean') return String(item);
    if (typeof item === 'object') {
      if ('symptom' in item) {
        const sev = (item.severity ?? item.Severity ?? '').toString();
        const name = String(item.symptom ?? '').trim();
        return name ? (sev ? `${name} (Severity: ${sev}/10)` : name) : null;
      }
      if ('value' in item) return String(item.value);
      if ('label' in item) return String(item.label);
      if ('name'  in item) return String(item.name);
      try { return JSON.stringify(item); } catch { return '[object]'; }
    }
    return String(item);
  }).filter(Boolean);
}
export default normalizeStringList;
