#!/usr/bin/env python3
"""PreToolUse guard: originals under sources/ are read-only. Defense in depth, not a sandbox.

Exit 2 blocks the tool call and shows stderr to Claude. Any other input passes through.
"""
import json
import os
from pathlib import Path
import re
import shlex
import sys

SOURCE = re.compile(r"(^|[\s'\"=/])(\./)?sources/")
MUTATING = re.compile(r"(^|[\s;&|(])(rm|rmdir|mv|touch|chmod|chown|chflags|ln|tee|truncate|dd|xattr|install|rsync|ditto)\b"
                      r"|(^|\s)sed\s+(-[a-zA-Z]*i|--in-place)")
REDIRECT = re.compile(r">>?\|?\s*([^\s;&|<>]+)")
OUTPUT_TOOLS = {"cp", "ffmpeg", "sips", "avconvert", "convert", "magick", "exiftool"}


def writes_into_sources(command):
    if not SOURCE.search(command):
        return False
    if MUTATING.search(command):
        return True
    if any(SOURCE.search(" " + target) for target in REDIRECT.findall(command)):
        return True
    try:
        words = shlex.split(command)
    except ValueError:
        return True
    for index, word in enumerate(words):
        name = word.rsplit("/", 1)[-1]
        if name in OUTPUT_TOOLS:
            # The output path is the last argument or follows -o/--out.
            rest = words[index + 1:]
            targets = rest[-1:] + [rest[i + 1] for i, w in enumerate(rest[:-1]) if w in {"-o", "--out", "--output"}]
            if any(SOURCE.search(" " + t) for t in targets):
                return True
    return False


def main():
    try:
        event = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    tool, data = event.get("tool_name", ""), event.get("tool_input", {}) or {}
    if tool in {"Edit", "Write", "NotebookEdit", "MultiEdit"}:
        path = str(data.get("file_path") or data.get("notebook_path") or "")
        project = Path(os.environ.get("CLAUDE_PROJECT_DIR") or event.get("cwd") or ".").resolve()
        if path and (project / path).resolve().is_relative_to(project / "sources"):
            print("Blocked: originals under sources/ are read-only. Write derived files to work/<run_id>/.", file=sys.stderr)
            return 2
    if tool == "Bash" and writes_into_sources(str(data.get("command", ""))):
        print("Blocked: this command could modify originals under sources/. Read them only; write outputs to work/<run_id>/.", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
