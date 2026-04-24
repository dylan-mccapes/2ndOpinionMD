import json, sys, requests
model = sys.argv[1] if len(sys.argv) > 1 else "eoh-llama-lucifer"
r = requests.post(
    "http://localhost:11434/api/chat",
    json={
        "model": model,
        "messages": [
            {"role": "user", "content": "Reply with exactly this JSON and nothing else: {\"answer\":\"OK\"}"}
        ],
        "stream": False,
        "options": {"temperature": 0.1},
    },
    timeout=180,
)
print("status", r.status_code)
print(r.text[:1500])
