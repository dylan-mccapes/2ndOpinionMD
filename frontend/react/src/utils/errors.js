export function toUserMessage(input) {
  if (typeof input === 'string') return input;

  if (input instanceof Error) return input.message || 'Something went wrong';

  const detail = input?.detail ?? input?.error ?? input;

  if (typeof detail === 'string') return detail;
  if (detail?.message) return detail.message;

  if (Array.isArray(detail) && detail.length) {
    const msgs = detail
      .map(e => e?.msg || e?.message)
      .filter(Boolean);
    if (msgs.length) return msgs.join('; ');
  }

  if (detail?.msg) return detail.msg;

  try { return JSON.stringify(detail); }
  catch { return 'Unexpected error'; }
}
