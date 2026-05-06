# CINDER — ACR Convergence 2026 handoff

This folder holds submission-facing drafts recovered from the Cinder v3 handoff (May 2026).

## About the `.tar.gz` that failed

If extraction produced only one file or a folder named like `*.tar.gz.834`:

- The `.834` suffix is **not** part of a normal gzip tarball name. It usually indicates an **incomplete download**, a **browser temp fragment**, or a renamed chunk—not a valid `tar.gz`.
- **Fix:** obtain the archive again from the source (email, Drive, CI artifact). Confirm integrity:

  ```bash
  gzip -t your_archive.tar.gz    # must exit 0
  tar -tzf your_archive.tar.gz   # list contents
  ```

- Then extract: `tar -xzf your_archive.tar.gz -C /desired/path`

Place any additional handoff files (`PROTOCOL_DRAFT_v3`, `KALEB_BRIEF_v2.md`, etc.) beside this README when you have the full bundle.

## Contents

| File | Notes |
|------|--------|
| `ACR_ABSTRACT_v2.md` | Draft v2 abstract (291 words); deadline 2026-06-09 submission window |
