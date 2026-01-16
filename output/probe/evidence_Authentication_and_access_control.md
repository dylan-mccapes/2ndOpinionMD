# Evidence for Authentication and access control

- `run_setup.py:0-5` → "role": "system",
- `run_setup.py:0-5` → {"role": "user", "content": prompt},
- `setup_chat_agents.py:0-5` → "Your role is EDUCATIONAL ONLY - explain concepts, don't suggest actions.",
- `setup_chat_agents.py:0-5` → context_parts.append("FILE RETRIEVAL POLICY:")
- `fmp/config/software_invariants.py:0-5` → "user_preference_variant_path": "User selection always overrides internal confidence heuristics; confidence informs recommendation, never permission.",
- `fmp/agents/triage_agent.py:0-5` → ROLE (STRICT):
- `fmp/agents/triage_agent.py:0-5` → {"role": "system", "content": system_prompt},
- `fmp/agents/triage_agent.py:0-5` → {"role": "user", "content": user_prompt},
