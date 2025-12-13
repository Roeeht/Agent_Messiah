#!/usr/bin/env python3

from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import httpx


def _print_action(action: str | None, payload: dict | None) -> None:
    if not action:
        return
    if payload:
        compact = json.dumps(payload, ensure_ascii=False)
        print(f"(action: {action} payload={compact})")
    else:
        print(f"(action: {action})")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Interactive text-only chat with Agent Messiah via /agent/turn")
    parser.add_argument("--base-url", default="http://localhost:8000", help="API base URL (default: http://localhost:8000)")
    parser.add_argument("--lead-id", type=int, default=1, help="Lead id to use (default: 1)")
    parser.add_argument("--timeout", type=float, default=45.0, help="HTTP timeout seconds (default: 45)")
    args = parser.parse_args(argv)

    base_url = args.base_url.rstrip("/")
    history: list[dict[str, Any]] = []

    print("Text chat started. Type /exit to quit.")
    print("Tip: The agent is configured to respond in English.")

    with httpx.Client(timeout=args.timeout) as client:
        while True:
            try:
                user_text = input("you> ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                break

            if not user_text:
                continue
            if user_text.lower() in {"/exit", "/quit", "exit", "quit"}:
                break

            req = {
                "lead_id": args.lead_id,
                "user_utterance": user_text,
                "history": history,
            }

            try:
                resp = client.post(f"{base_url}/agent/turn", json=req)
                resp.raise_for_status()
                data = resp.json()
            except httpx.HTTPStatusError as e:
                body = e.response.text
                print(f"error> HTTP {e.response.status_code}: {body}")
                continue
            except Exception as e:
                print(f"error> {e}")
                continue

            agent_reply = (data.get("agent_reply") or "").strip()
            action = data.get("action")
            action_payload = data.get("action_payload")

            if not agent_reply:
                print("agent> (empty response)")
            else:
                print(f"agent> {agent_reply}")

            _print_action(action, action_payload if isinstance(action_payload, dict) else None)

            history.append({"role": "user", "content": user_text})
            history.append({"role": "assistant", "content": agent_reply})

            if action == "end_call":
                break

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
