# Report: OpenAI API key handling and simplification

**Date:** 2026-03-27  
**Context:** Timeline PDF / EoH pipeline (`run_eohd_timeline_pdf.py`, `timeline_summarizer.py`, `server/llm/llm_client.py`).

## What was going wrong

1. **Same symptom everywhere (401 `invalid_api_key`)**  
   PDF batch extraction, gap agent, hierarchical map steps, and the summarizer all call OpenAI. When the platform rejects the credential, every stage fails the same way. That points to **the secret string or endpoint**, not to a single feature.

2. **Environment vs. what the SDK actually sends**  
   Keys are often broken without looking broken: trailing newline from `export VAR="$(pbpaste)"`, a BOM from a UTF-8 file, line breaks in the middle of the key, or NBSP from copy/paste. **`strip()` only removes ends**, not internal whitespace.

3. **Two client styles in one process**  
   The CLI constructs **`AsyncOpenAI`**, while much of the stack historically used **`OpenAI`** via a lazy singleton in `llm_client.py`. For a while, **`chat_completion_async` ignored the passed-in client** and always used the global sync client—so behavior depended on whatever that singleton read from the environment, not on the CLI instance. That is now fixed (explicit `AsyncOpenAI` is honored when provided), but the **duplication of “how we get a client”** remains.

4. **No fail-fast**  
   A bad key was only discovered after expensive work (large PDF batches, many chunks). A tiny verification call up front surfaces the same 401 in seconds.

## What the recent code does (and why it feels like “a lot”)

| Piece | Purpose |
|--------|--------|
| **`sanitize_openai_api_key`** | Remove BOM and **all** whitespace from the key string (valid keys do not contain spaces). |
| **`reset_openai_sync_client`** | If `OPENAI_API_KEY` is corrected in-process, clear the lazy sync client so the next `get_client()` does not keep an old instance. |
| **`chat_completion_async` branches** | Use **`AsyncOpenAI`** when callers pass it; otherwise fall back to sync **`OpenAI`** + thread pool. |
| **CLI: normalize env + optional `--api-key-file`** | One place to load a clean key; file avoids shell quoting and accidental newlines. |
| **CLI: default “ping”** | One minimal `gpt-4o-mini` completion before the PDF run to fail fast on 401. |
| **`OPENAI_BASE_URL` log** | Reminder that a custom base URL implies a different auth story (proxy / nonstandard deployment). |

None of this changes OpenAI’s rules; it only reduces **footguns** and **debugging time**.

## Suggestions to simplify (later)

1. **Single factory module**  
   One small module, e.g. `server/llm/openai_config.py`, exporting:
   - `get_sanitized_api_key() -> str | None`
   - `make_async_client() -> AsyncOpenAI`
   - `make_sync_client() -> OpenAI`  
   Call sites (CLI, `llm_client`, one-off scripts) import these instead of re-implementing env + sanitize.

2. **Prefer one async path for new code**  
   Long term, route timeline + gap agents through **one** `AsyncOpenAI` created at the entrypoint and passed down, and **thin** wrappers for rate limits / retries only—avoid maintaining parallel sync + async client creation.

3. **Make the ping optional or environment-gated**  
   Default on for CLI is reasonable; for tests or internal batch jobs, `SKIP_OPENAI_PING=1` or `--skip-openai-ping` (already present) keeps behavior explicit without deleting the guardrail.

4. **Document one “golden path” for founders**  
   Keep operational docs to: “Put key in a file with no newline; run with `--api-key-file`.” That avoids expanding code for every edge case.

5. **Audit `load_dotenv` usage**  
   Any `load_dotenv(..., override=True)` that runs after the shell exports a good key can **overwrite** it with a stale `.env`. Centralizing dotenv load (or documenting “no override in worker processes”) prevents mysterious “it works in my shell but not in the app” cases.

6. **Remove duplication once stable**  
   After a few weeks without key incidents, consider collapsing CLI-only logic (sanitize + ping) into the shared factory so `run_eohd_timeline_pdf.py` stays thin.

## Bottom line

The extra code is not “OpenAI requiring ceremony”; it addresses **real failure modes** (dirty strings, two client types, ignored client argument, late failure). Simplification should come from **centralizing** key resolution and client construction, not from removing sanitization or fail-fast checks until a single factory is in place.

For your immediate run, following the **file-based key + `--api-key-file`** steps is the right operational choice; no further code changes are required for that path.
