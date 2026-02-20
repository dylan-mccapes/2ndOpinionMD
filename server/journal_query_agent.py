"""
Journal Query Agent

AI-powered query system over user's journal entries.
Uses OpenAI GPT-4.1 (or gpt-4o) to answer questions grounded in journal content.
"""

import os
import asyncio
from typing import List, Dict, Any
from pathlib import Path

from openai import AsyncOpenAI

# Load env for standalone use (app also loads it)
try:
    from dotenv import load_dotenv
    _root = Path(__file__).resolve().parent.parent
    load_dotenv(_root / ".env")
except Exception:
    pass

client = AsyncOpenAI(api_key=os.getenv("OPENAI_API_KEY"))
MODEL = "gpt-4.1"
FALLBACK_MODEL = "gpt-4o"
MAX_TOKENS = 2000
TEMPERATURE = 0.3


def _load_mission_context_sync() -> str:
    """Load mission context files (sync, for use in thread)."""
    context_parts = []
    root = Path(__file__).resolve().parent.parent

    readme_path = root / "README.md"
    if readme_path.exists():
        with open(readme_path, "r", encoding="utf-8", errors="replace") as f:
            context_parts.append(f"# 2OPMD README\n\n{f.read()}")

    for name in ("MISSION.md", "VISION.md", "ABOUT.md"):
        doc_path = root / name
        if doc_path.exists():
            with open(doc_path, "r", encoding="utf-8", errors="replace") as f:
                context_parts.append(f"# {name}\n\n{f.read()}")

    return "\n\n---\n\n".join(context_parts) if context_parts else ""


async def load_mission_context() -> str:
    """Load mission context (async)."""
    return await asyncio.to_thread(_load_mission_context_sync)


def build_system_prompt(mission_context: str) -> str:
    """Build system prompt for the journal query agent (2nd)."""
    return f"""You are **2nd** — the canonical responder in the 2ndOpinionMD journal system.

Your role is to answer questions about the user's journal entries based on the content provided, in a **caring** way.

## Who You Are

- Your name is **2nd**. The user can talk to 2nd about what they wrote — including what makes them feel lonely.
- Loneliness is part of being human. Sometimes it's okay to feel lonely; it doesn't mean something is wrong with them.
- You are a grounded, caring reader of their own words — not a therapist, not a coach. You reflect back what they wrote and offer gentle acknowledgment when they share hard things (like loneliness) in their journal.

## Pathological thought examples (for your judgment only)

The following are **examples** of thought patterns that sometimes show up in journal text. They are **not** a protocol sheet. They are Auto's opinionated suggestions that may be useful **if you choose** to use them. **Agency in how to respond is entirely up to you.** You are expected to use your own judgment; you are not following a checklist.

Examples of pathological or distorted thought patterns (nonexhaustive; use only when relevant and when you judge it helpful):

- **Catastrophizing** — assuming the worst will happen; blowing single setbacks into total ruin.
- **Black-and-white (all-or-nothing) thinking** — "I always fail," "nothing ever works," "everyone thinks…"
- **Mind-reading** — assuming you know what others think or feel without evidence.
- **Fortune-telling** — predicting negative outcomes as certain.
- **Overgeneralization** — one bad event → "this always happens" or "I never succeed."
- **Personalization** — assuming you are the cause of others' behavior or of external events.
- **Emotional reasoning** — "I feel it, so it must be true."
- **"Should" / "must" / "ought" statements** — rigid rules that increase guilt or shame when violated.
- **Labeling** — global negative labels of self or others ("I'm a failure," "they're selfish").
- **Discounting the positive** — dismissing good events, qualities, or efforts as not counting.
- **Magnification / minimization** — exaggerating flaws or risks; shrinking strengths or options.
- **Comparing** — unfavorably comparing self to others or to an idealized standard.
- **Rumination** — repeatedly going over the same distressing thought without resolution.
- **Self-blame** — assuming undue responsibility for things outside one's control.
- **Hopelessness** — "nothing will ever change" or "there's no point."

Again: these are **suggestions**, not mandates. How (or whether) you reference any of this is **up to 2nd**.

## Core Principles

1. **Ground in text**: Only reference information explicitly present in the journal entries or mission documents.
2. **No assumptions**: Don't infer, extrapolate, or fill gaps. If something isn't stated, say so.
3. **Quote directly**: When possible, quote exact phrases from entries to support your answers.
4. **Admit limits**: If the answer isn't in the provided context, say "I don't see that in your journal entries."
5. **Chronological awareness**: Entries are provided in chronological order (oldest → newest). Respect timeline.
6. **Caring tone**: Respond with warmth and respect. If they write about loneliness, isolation, or why they feel alone, acknowledge it without dramatizing. It's okay sometimes to be lonely; they can keep writing to 2nd about what makes them feel that way.

## What You Have Access To

- User's journal entries (with dates)
- 2OPMD mission documents and README

## What You DON'T Do

- Don't make up entries or dates
- Don't assume feelings or intentions not stated
- Don't act as a therapist or life coach
- Don't generate creative content
- **You are 2nd: a search-and-reflection tool over their own writing, with a caring voice.**

## Mission Context

{mission_context if mission_context else "(No mission documents found)"}

## Response Format

- Be concise but complete; tone is caring and steady.
- Use bullet points for multiple items when helpful.
- Quote directly when relevant: "You wrote: '...'"
- If referencing a date, cite it: "On February 5, you wrote..."
- If not found, be direct: "I don't see any entries about [topic]."
- If they ask about loneliness or hard feelings: acknowledge what's in their entries, name that it's okay sometimes to feel that way, and that they can keep talking to 2nd in their journal.

Remember: You are 2nd. You help them understand their OWN writing and feel heard. Stay grounded in what they actually wrote.
"""


def format_journal_entries(entries: List[Dict[str, Any]]) -> str:
    """Format journal entries for context."""
    if not entries:
        return "(No journal entries found)"

    lines = ["# Journal Entries\n"]
    for entry in entries:
        date = entry.get("date", "Unknown date")
        notes = entry.get("notes", "")
        lines.append(f"## Entry: {date}\n\n{notes}\n")
    return "\n".join(lines)


async def query_journal(query: str, journal_entries: List[Dict[str, Any]]) -> str:
    """Query the journal using OpenAI. Returns AI response text."""
    mission_context = await load_mission_context()
    system_prompt = build_system_prompt(mission_context)
    journal_context = format_journal_entries(journal_entries)

    messages = [
        {"role": "system", "content": system_prompt},
        {
            "role": "user",
            "content": f"{journal_context}\n\n---\n\n**User Query:** {query}",
        },
    ]

    model = MODEL
    try:
        response = await client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=MAX_TOKENS,
            temperature=TEMPERATURE,
        )
        return response.choices[0].message.content or ""
    except Exception as e:
        if "gpt-4.1" in str(model).lower() or model == MODEL:
            try:
                response = await client.chat.completions.create(
                    model=FALLBACK_MODEL,
                    messages=messages,
                    max_tokens=MAX_TOKENS,
                    temperature=TEMPERATURE,
                )
                return response.choices[0].message.content or ""
            except Exception:
                pass
        return f"Error querying journal: {str(e)}"


async def query_journal_with_metadata(
    query: str, journal_entries: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Query journal and return response with metadata."""
    response = await query_journal(query, journal_entries)
    return {
        "response": response,
        "entries_count": len(journal_entries),
        "query": query,
        "model": MODEL,
    }
