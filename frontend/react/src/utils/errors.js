export function toUserMessage(input) {
  if (typeof input === 'string') {
    if (input.includes('<!DOCTYPE html>') || input.includes('<html')) {
      const preMatch = input.match(/<pre>(.*?)<\/pre>/s);
      if (preMatch) return preMatch[1].trim();
      
      const titleMatch = input.match(/<title>(.*?)<\/title>/s);
      if (titleMatch && titleMatch[1] !== 'Error') return titleMatch[1].trim();
      
      return 'Server error occurred. Please try again.';
    }
    return input;
  }

  if (input instanceof Error) return input.message || 'Something went wrong';

  const detail = input?.detail ?? input?.error ?? input;

  if (typeof detail === 'string') {
    if (detail.includes('<!DOCTYPE html>') || detail.includes('<html')) {
      const preMatch = detail.match(/<pre>(.*?)<\/pre>/s);
      if (preMatch) return preMatch[1].trim();
      return 'Server error occurred. Please try again.';
    }
    return detail;
  }
  
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
