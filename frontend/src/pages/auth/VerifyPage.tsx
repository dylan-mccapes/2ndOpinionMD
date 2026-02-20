export function VerifyPage() {
  return (
    <div className="max-w-md mx-auto mt-12">
      <h1
        className="text-xl font-mono font-bold mb-6"
        style={{ color: 'var(--text-primary)' }}
      >
        EMAIL VERIFICATION
      </h1>

      <div
        className="p-6 rounded border text-center"
        style={{
          backgroundColor: 'var(--bg-secondary)',
          borderColor: 'var(--border-color)',
        }}
      >
        <p
          className="text-sm"
          style={{ color: 'var(--text-secondary)' }}
        >
          Verification handler placeholder. Awaiting Phase 4 implementation.
        </p>
      </div>
    </div>
  );
}
