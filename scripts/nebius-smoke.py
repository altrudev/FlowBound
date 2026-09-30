#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
import urllib.request

BASE_URL = os.getenv("NEBIUS_BASE_URL", "https://api.tokenfactory.nebius.com/v1/").rstrip("/")
MODEL = os.getenv("NEBIUS_MODEL", "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B")
KEY = os.getenv("NEBIUS_API_KEY") or os.getenv("NEBIUS_TOKEN_FACTORY_API_KEY")

if not KEY:
    raise SystemExit("Set NEBIUS_API_KEY or NEBIUS_TOKEN_FACTORY_API_KEY first.")


def request(path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        BASE_URL + path,
        data=data,
        headers={
            "Authorization": "Bearer " + KEY,
            "Content-Type": "application/json",
        },
        method="GET" if payload is None else "POST",
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.load(response)


models = request("/models")
ids = {str(item.get("id")) for item in models.get("data", [])}
print(f"Token Factory authenticated; models visible: {len(ids)}")
print(f"Configured NVIDIA model available: {MODEL in ids}")
if MODEL not in ids:
    print("Configured model is not available to this key.", file=sys.stderr)
    raise SystemExit(2)

completion = request(
    "/chat/completions",
    {
        "model": MODEL,
        "temperature": 0,
        "max_tokens": 80,
        "messages": [
            {
                "role": "user",
                "content": (
                    "Return JSON only: "
                    '{"status":"ok","role":"bounded-proposal-smoke-test"}'
                ),
            }
        ],
    },
)
message = completion["choices"][0]["message"]["content"]
print("Live inference succeeded.")
print(message[:300])
