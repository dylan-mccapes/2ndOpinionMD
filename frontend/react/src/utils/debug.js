
export const isDebug =
  (typeof process !== 'undefined' && process.env.NODE_ENV !== 'production') ||
  (typeof window !== 'undefined' && /(?:^|[?&])debug=1(?:$|&)/.test(window.location.search));

export function saveDebugInfo(...args) { if (isDebug) console.log('[saveDebugInfo]', ...args); }
export function updateDebugPanel(...args) { if (isDebug) console.log('[updateDebugPanel]', ...args); }
export function clearDebugInfo(...args) { if (isDebug) console.log('[clearDebugInfo]', ...args); }
export function createPersistentDebugPanel(...args) { if (isDebug) console.log('[createPersistentDebugPanel]', ...args); }

export function setBreakpointIfEnabled(label = 'debug-breakpoint') {
  if (isDebug) {
    // eslint-disable-next-line no-debugger
    debugger;
    console.log(`[breakpoint] ${label}`);
  }
}
