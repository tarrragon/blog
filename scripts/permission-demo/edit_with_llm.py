#!/usr/bin/env python3
"""
Demo: LLM has no file system access. The wrapper does.
Permission gates live in the wrapper, not in the model.

Three modes show the spectrum of trust:
  --dry-run     : show what the LLM proposed, don't touch the file (safest)
  --confirm     : show diff, prompt user before applying
  --auto        : apply blindly (most dangerous — only for trusted automation)

Usage:
    python3 edit_with_llm.py FILE INSTRUCTION [--dry-run | --confirm | --auto]
"""
import argparse
import difflib
import json
import re
import sys
import urllib.request
from pathlib import Path

CHAT_URL = "http://localhost:11434/v1/chat/completions"


def chat(messages: list[dict], model: str = "gemma3:1b") -> str:
    payload = json.dumps({"model": model, "messages": messages, "stream": False}).encode()
    req = urllib.request.Request(
        CHAT_URL,
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(req, timeout=180) as resp:
        return json.loads(resp.read())["choices"][0]["message"]["content"]


def extract_code_block(text: str) -> str | None:
    """Pull the first fenced code block out of LLM output.

    Accept both well-formed (```lang\n...\n```) and missing-closing-fence cases
    — small models often forget the closing fence.
    """
    # Try well-formed first
    m = re.search(r"```(?:\w+)?\n(.*?)\n```", text, re.DOTALL)
    if m:
        return m.group(1)
    # Fallback: opening fence + everything after
    m = re.search(r"```(?:\w+)?\n(.*)", text, re.DOTALL)
    if m:
        # Strip a trailing fence if present
        return re.sub(r"\n```\s*$", "", m.group(1))
    return None


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("file", type=Path)
    ap.add_argument("instruction")
    g = ap.add_mutually_exclusive_group()
    g.add_argument("--dry-run", action="store_true", default=True)
    g.add_argument("--confirm", action="store_true")
    g.add_argument("--auto", action="store_true")
    ap.add_argument("--model", default="gemma3:1b")
    args = ap.parse_args()

    if not args.file.exists():
        print(f"ERROR: {args.file} not found", file=sys.stderr)
        sys.exit(1)

    original = args.file.read_text(encoding="utf-8")

    system = (
        "You modify text files. Output ONLY the complete new file content inside a "
        "single ```markdown code block. No prose before or after. No explanations."
    )
    user = f"File path: {args.file}\n\nCurrent content:\n\n{original}\n\nInstruction: {args.instruction}"

    print(f"[+] Asking {args.model} to: {args.instruction!r}", file=sys.stderr)
    response = chat([
        {"role": "system", "content": system},
        {"role": "user", "content": user},
    ], model=args.model)

    new_content = extract_code_block(response)
    if new_content is None:
        print("ERROR: LLM did not return a code block. Raw response:", file=sys.stderr)
        print(response, file=sys.stderr)
        sys.exit(1)

    # Show diff regardless of mode — diff is read-only, always safe
    diff = list(difflib.unified_diff(
        original.splitlines(keepends=True),
        new_content.splitlines(keepends=True),
        fromfile=f"a/{args.file.name}",
        tofile=f"b/{args.file.name}",
    ))
    if diff:
        print("[+] Proposed diff:", file=sys.stderr)
        sys.stdout.writelines(diff)
    else:
        print("[+] LLM proposed no changes.", file=sys.stderr)
        sys.exit(0)

    # PERMISSION GATE — wrapper decides whether to apply
    if args.auto:
        print(f"\n[!] --auto mode: writing without confirmation", file=sys.stderr)
        args.file.write_text(new_content, encoding="utf-8")
        print(f"[+] wrote {args.file}", file=sys.stderr)
    elif args.confirm:
        print(f"\n[?] Apply this change to {args.file}? [y/N] ", end="", file=sys.stderr, flush=True)
        ans = input().strip().lower()
        if ans == "y":
            args.file.write_text(new_content, encoding="utf-8")
            print(f"[+] wrote {args.file}", file=sys.stderr)
        else:
            print(f"[-] aborted, file unchanged", file=sys.stderr)
    else:
        # default: dry-run, never write
        print(f"\n[+] --dry-run: file unchanged. Use --confirm or --auto to apply.", file=sys.stderr)


if __name__ == "__main__":
    main()
