"""Entry point for the mock server."""
from __future__ import annotations

import argparse
import os

import uvicorn

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run 2OPMD UX mock server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8100)
    parser.add_argument("--role", choices=["patient", "doctor"], default=None, help="Mock auth role for /api/auth/me")
    parser.add_argument("--timeline-json", default=None, help="Path to PTV JSON used by mock timeline + graph demo")
    parser.add_argument("--llm-model", default=None, help="Override mock LLM model (default: eoh-llama-lucifer)")
    parser.add_argument("--ollama-url", default=None, help="Override Ollama URL for mock LLM calls")
    parser.add_argument("--no-llm", action="store_true", help="Disable graph+LLM chat responses, use static replies")
    args = parser.parse_args()

    if args.role:
        os.environ["MOCK_USER_TYPE"] = args.role
    if args.timeline_json:
        os.environ["MOCK_GRAPH_PTV_JSON"] = args.timeline_json
        os.environ["DEV_TIMELINE_VISION_FILE"] = args.timeline_json
    if args.llm_model:
        os.environ["MOCK_OLLAMA_MODEL"] = args.llm_model
    if args.ollama_url:
        os.environ["MOCK_OLLAMA_URL"] = args.ollama_url
    if args.no_llm:
        os.environ["MOCK_CHAT_USE_LLM"] = "false"

    uvicorn.run(
        "server.mock.app:app",
        host=args.host,
        port=args.port,
        reload=True,
        reload_dirs=["server/mock", "server/graph_traversal", "server/eoh"],
        log_level="info",
    )
