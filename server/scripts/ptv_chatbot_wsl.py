#!/usr/bin/env python3
"""
ptv_chatbot_wsl.py — interactive PTV chat using the same retrieval loop as the harness.

Runs on **Windows PowerShell** (Ollama on ``127.0.0.1``) or **WSL/Linux**. On Windows, prefer::

    .\\server\\scripts\\ptv_chatbot.ps1

Uses ``server.ptv_toolkit``: load graph once, then for each user line call ``run_agent``
(plan → tools → final_answer) against Ollama.

**Model name:** use whatever ``ollama list`` shows (e.g. ``eoh-llama-lucifer`` or
``eoh-llama3.1:8b-lucifer`` after you create the model from the Modelfile).

**Ollama from WSL when Ollama runs on Windows:** ``127.0.0.1`` inside WSL is **not** the
Windows loopback — you will get *connection refused*. Use either:

- ``--wsl-host`` — script picks the Windows host IP (from ``/etc/resolv.conf`` or
  ``ip route show default``) and uses ``http://<that>:11434``, or
- ``export PTV_OLLAMA_URL="http://$(grep nameserver /etc/resolv.conf | awk '{print $2}'):11434"``

On Windows, set Ollama to listen on all interfaces (e.g. ``OLLAMA_HOST=0.0.0.0``) and allow
port 11434 through the firewall from WSL.

Or pass ``--ollama-url`` explicitly. Prefer ``PTV_OLLAMA_URL`` for the **client** URL;
do not reuse Windows ``OLLAMA_HOST=0.0.0.0`` here (that is the bind address, not the host to call).

**First semantic question:** the first ``semantic_search`` may build embeddings (1–5+ minutes);
later turns reuse the cache under ``~/.cache`` / project cache as configured in embeddings.py.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, Optional

import requests

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from server.ptv_toolkit import build_handoff, load_graph, save_handoff  # noqa: E402
from server.ptv_toolkit.agent import log_to_dict, run_agent  # noqa: E402
from server.ptv_toolkit.registry import tool_names  # noqa: E402


def _default_ollama_url() -> str:
    """Client URL for HTTP requests. Prefer PTV_OLLAMA_URL or OLLAMA_BASE_URL."""
    u = (os.environ.get("PTV_OLLAMA_URL") or os.environ.get("OLLAMA_BASE_URL") or "").strip()
    if not u:
        return "http://127.0.0.1:11434"
    if u.startswith("http://") or u.startswith("https://"):
        return u.rstrip("/")
    if "://" not in u:
        return f"http://{u}".rstrip("/")
    return u.rstrip("/")


def _guess_windows_host_for_wsl() -> Optional[str]:
    """
    Best-effort IP of the Windows host as seen from WSL2.

    Tries /etc/resolv.conf nameserver (skip loopback), then ``ip route show default``.
    """
    nameservers: list[str] = []
    try:
        text = Path("/etc/resolv.conf").read_text(encoding="utf-8", errors="replace")
        for line in text.splitlines():
            line = line.strip()
            if line.startswith("nameserver ") and len(line.split()) >= 2:
                nameservers.append(line.split()[1])
    except OSError:
        pass

    for ip in nameservers:
        if ip and ip not in ("127.0.0.1", "::1"):
            return ip

    try:
        out = subprocess.run(
            ["ip", "route", "show", "default"],
            capture_output=True,
            text=True,
            timeout=3,
            check=False,
        )
        if out.returncode == 0 and out.stdout:
            m = re.search(r"\bvia\s+([0-9.]+)\b", out.stdout)
            if m:
                return m.group(1)
    except (FileNotFoundError, subprocess.TimeoutExpired, OSError):
        pass

    for ip in nameservers:
        if ip:
            return ip
    return None


def _ollama_url_for_host(host: str, port: int) -> str:
    host = host.strip().rstrip("/")
    if host.startswith("http://") or host.startswith("https://"):
        return host.rstrip("/")
    return f"http://{host}:{port}"


def _probe_ollama(url: str, timeout: float = 2.0) -> bool:
    base = url.rstrip("/")
    try:
        r = requests.get(f"{base}/api/tags", timeout=timeout)
        return r.status_code == 200
    except OSError:
        return False
    except requests.RequestException:
        return False


def _ollama_connection_hint(current_url: str) -> str:
    guess = _guess_windows_host_for_wsl()
    lines = [
        f"[ptv-chat] Could not reach Ollama at {current_url}.",
        "[ptv-chat] From WSL2, 127.0.0.1 is usually **this Linux VM**, not Windows where "
        "Ollama often runs.",
    ]
    if guess:
        alt = _ollama_url_for_host(guess, 11434)
        lines.append(
            f"[ptv-chat] Try:  --wsl-host   (uses {alt})  "
            f"or  --ollama-url {alt}"
        )
    else:
        lines.append(
            "[ptv-chat] Try:  export PTV_OLLAMA_URL='http://<windows-host-ip>:11434'  "
            "(see Windows ipconfig / WSL resolv.conf)."
        )
    lines.append(
        "[ptv-chat] On Windows: OLLAMA_HOST=0.0.0.0 and firewall allow TCP 11434 from WSL."
    )
    return "\n".join(lines)


def _print_turns_summary(log_dict: Dict[str, Any], verbose: bool) -> None:
    seq = log_dict.get("tool_call_sequence") or []
    print(f"  [trace] tools: {seq}  stopped: {log_dict.get('reason_stopped')}  "
          f"{log_dict.get('elapsed_sec')}s")
    if verbose:
        for t in log_dict.get("turns") or []:
            role = t.get("role")
            tool = t.get("tool")
            err = t.get("parse_error")
            prev = (t.get("content_preview") or "")[:200]
            extra = f" parse_error={err!r}" if err else ""
            print(f"    {role}" + (f" tool={tool}" if tool else "") + extra)
            if prev:
                print(f"      {prev!r}")


def _print_answer(log_dict: Dict[str, Any]) -> None:
    fa = log_dict.get("final_answer") or {}
    ans = fa.get("answer")
    ev = fa.get("evidence_event_ids") or []
    if ans:
        print("\n--- Answer ---\n")
        print(ans)
    else:
        print("\n(No final_answer — model may have hit max turns or Ollama error.)")
    if ev:
        print(f"\nEvidence event_ids ({len(ev)}): {', '.join(ev[:20])}")
        if len(ev) > 20:
            print(f"  ... and {len(ev) - 20} more")


def main() -> int:
    ap = argparse.ArgumentParser(description="Interactive PTV chat (WSL-friendly).")
    ap.add_argument(
        "--graph",
        default=str(
            ROOT / "artifacts" / "forward_kaleb_package_20260423" / "PTV_REAL_EHR_20260423.json"
        ),
        help="Path to indexed PTV JSON.",
    )
    ap.add_argument(
        "--model",
        default=os.environ.get("PTV_OLLAMA_MODEL", "eoh-llama-lucifer"),
        help="Ollama model name (e.g. eoh-llama-lucifer or eoh-llama3.1:8b-lucifer).",
    )
    ap.add_argument(
        "--ollama-url",
        default="",
        help="Ollama base URL (default: PTV_OLLAMA_URL, else OLLAMA_BASE_URL, else http://127.0.0.1:11434).",
    )
    ap.add_argument(
        "--wsl-host",
        action="store_true",
        help="Use Windows host IP from WSL2 (resolv.conf / default route); overrides --ollama-url.",
    )
    ap.add_argument(
        "--auto-wsl-host",
        action="store_true",
        help="If Ollama is unreachable at the chosen URL, try Windows host IP once (WSL2).",
    )
    ap.add_argument(
        "--ollama-port",
        type=int,
        default=11434,
        help="Port when using --wsl-host (default 11434).",
    )
    ap.add_argument(
        "--skip-ollama-probe",
        action="store_true",
        help="Do not GET /api/tags at startup (offline / faster).",
    )
    ap.add_argument("--max-turns", type=int, default=8, help="Tool-call budget (plan excluded).")
    ap.add_argument("--temperature", type=float, default=0.1)
    ap.add_argument("--timeout", type=float, default=300.0)
    ap.add_argument("--verbose", "-v", action="store_true", help="Print per-turn trace.")
    ap.add_argument(
        "--save-handoffs",
        default="",
        help="If set, directory to write .handoff.json after each answer.",
    )
    ap.add_argument(
        "--transcript",
        default="",
        help="Append JSON lines (question + log_to_dict) to this file.",
    )
    args = ap.parse_args()

    graph_path = Path(args.graph).expanduser().resolve()
    if not graph_path.is_file():
        print(f"Graph not found: {graph_path}", file=sys.stderr)
        return 1

    ollama_url = (args.ollama_url or "").strip() or _default_ollama_url()

    if args.wsl_host:
        wh = _guess_windows_host_for_wsl()
        if not wh:
            print(
                "[ptv-chat] --wsl-host: could not infer Windows host IP "
                "(check /etc/resolv.conf and `ip route show default`).",
                file=sys.stderr,
            )
            return 1
        ollama_url = _ollama_url_for_host(wh, int(args.ollama_port))
        print(f"[ptv-chat] --wsl-host → {ollama_url}", flush=True)

    if args.auto_wsl_host and not args.wsl_host:
        if not args.skip_ollama_probe and not _probe_ollama(ollama_url):
            guess = _guess_windows_host_for_wsl()
            if guess:
                candidate = _ollama_url_for_host(guess, int(args.ollama_port))
                if _probe_ollama(candidate):
                    print(
                        f"[ptv-chat] Ollama not at {ollama_url}; using --auto-wsl-host → {candidate}",
                        flush=True,
                    )
                    ollama_url = candidate

    if not args.skip_ollama_probe and not _probe_ollama(ollama_url):
        print(_ollama_connection_hint(ollama_url), flush=True)
        if "127.0.0.1" in ollama_url or "localhost" in ollama_url.lower():
            print(
                "[ptv-chat] Continuing anyway — first question will fail until URL is fixed.",
                flush=True,
            )

    print("[ptv-chat] loading graph …", flush=True)
    gh = load_graph(graph_path)
    n = len(gh.events)
    print(f"[ptv-chat] {n} events | hash {gh.graph_hash}")
    print(f"[ptv-chat] model={args.model!r}  ollama={ollama_url}")
    print(f"[ptv-chat] tools: {tool_names()}")
    print(
        "[ptv-chat] first semantic_search may build embeddings (slow once). "
        "Commands: quit | exit | q  |  /verbose  |  /help",
        flush=True,
    )

    handoff_dir: Optional[Path] = None
    if args.save_handoffs:
        handoff_dir = Path(args.save_handoffs).expanduser().resolve()
        handoff_dir.mkdir(parents=True, exist_ok=True)

    transcript_path = Path(args.transcript).expanduser().resolve() if args.transcript else None
    verbose = bool(args.verbose)

    banner = (
        "\nAsk a question about this chart (natural language). "
        "The agent uses the same toolkit as the harness.\n"
    )
    print(banner)

    turn_n = 0
    while True:
        try:
            line = input("ptv> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n[ptv-chat] bye.")
            return 0

        if not line:
            continue

        low = line.lower()
        if low in ("quit", "exit", "q", ":q"):
            print("[ptv-chat] bye.")
            return 0
        if low == "/help":
            print(
                "  quit | exit | q     — leave\n"
                "  /verbose            — toggle tool trace after each answer\n"
                "  /tools              — list toolkit tool names\n"
                "  anything else       — sent to the agent as a question\n"
                "\n"
                "If Ollama runs on Windows, start with:  "
                "python3 server/scripts/ptv_chatbot_wsl.py ... --wsl-host\n"
            )
            continue
        if low == "/verbose":
            verbose = not verbose
            print(f"[ptv-chat] verbose = {verbose}")
            continue
        if low == "/tools":
            print(tool_names())
            continue

        turn_n += 1
        print(f"[ptv-chat] thinking… (turn {turn_n})", flush=True)
        log = run_agent(
            gh,
            line,
            model=args.model,
            ollama_url=ollama_url,
            max_turns=args.max_turns,
            temperature=args.temperature,
            timeout=args.timeout,
        )
        d = log_to_dict(log)
        _print_turns_summary(d, verbose)
        rs = str(d.get("reason_stopped") or "")
        if rs.startswith("ollama_error") and (
            "Connection refused" in rs or "Failed to establish" in rs
        ):
            print(_ollama_connection_hint(ollama_url), flush=True)
        _print_answer(d)

        if handoff_dir is not None:
            ho = build_handoff(gh, log)
            path = handoff_dir / f"chat_{turn_n:04d}.handoff.json"
            save_handoff(ho, path)
            print(f"\n[ptv-chat] handoff → {path}")

        if transcript_path is not None:
            row = {"turn": turn_n, "user": line, "agent": d}
            with transcript_path.open("a", encoding="utf-8") as fh:
                fh.write(json.dumps(row, default=str) + "\n")
            print(f"[ptv-chat] transcript append → {transcript_path}")

        print()


if __name__ == "__main__":
    raise SystemExit(main())
