#!/usr/bin/env python3.11
from __future__ import annotations

import json
import os
import argparse
import subprocess
import sys
import threading
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
BINARY = Path(os.environ.get("CODEBASE_MEMORY_BIN", ROOT / "storage/runtime/bin/codebase-memory-mcp"))
CACHE_DIR = Path(os.environ.get("CBM_CACHE_DIR", ROOT / "storage/codebase-memory"))
ALLOWED_TOOLS = {
    "detect_changes",
    "get_architecture",
    "get_code_snippet",
    "get_graph_schema",
    "index_status",
    "query_graph",
    "search_code",
    "search_graph",
    "trace_call_path",
    "trace_path",
}


def copy_stderr(stream: Any) -> None:
    for line in stream:
        sys.stderr.write(line)
        sys.stderr.flush()


def error_response(request_id: Any, message: str) -> dict[str, Any]:
    return {
        "jsonrpc": "2.0",
        "id": request_id,
        "error": {"code": -32601, "message": message},
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Read-only, optionally project-scoped Codebase Memory MCP proxy.")
    parser.add_argument("--project", help="Reject calls for other Codebase Memory projects.")
    args = parser.parse_args()
    if not BINARY.exists():
        print(f"Codebase Memory binary is missing: {BINARY}", file=sys.stderr)
        return 1
    env = os.environ.copy()
    env["CBM_CACHE_DIR"] = str(CACHE_DIR)
    process = subprocess.Popen(
        [str(BINARY)],
        cwd=str(ROOT),
        env=env,
        text=True,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        bufsize=1,
    )
    assert process.stdin is not None
    assert process.stdout is not None
    assert process.stderr is not None
    threading.Thread(target=copy_stderr, args=(process.stderr,), daemon=True).start()

    try:
        for raw_line in sys.stdin:
            try:
                request = json.loads(raw_line)
            except json.JSONDecodeError:
                print(json.dumps(error_response(None, "invalid JSON-RPC request")), flush=True)
                continue
            request_id = request.get("id")
            if request.get("method") == "tools/call":
                tool_name = (request.get("params") or {}).get("name")
                if tool_name not in ALLOWED_TOOLS:
                    print(
                        json.dumps(
                            error_response(request_id, f"tool is blocked by AI Docs Hub policy: {tool_name}")
                        ),
                        flush=True,
                    )
                    continue
                tool_arguments = (request.get("params") or {}).setdefault("arguments", {})
                requested_project = tool_arguments.get("project")
                if args.project and requested_project and requested_project != args.project:
                    print(
                        json.dumps(
                            error_response(
                                request_id,
                                f"proxy is scoped to project '{args.project}', not '{requested_project}'",
                            )
                        ),
                        flush=True,
                    )
                    continue
                if args.project:
                    tool_arguments["project"] = args.project

            process.stdin.write(json.dumps(request, ensure_ascii=False) + "\n")
            process.stdin.flush()
            if request_id is None:
                continue
            while True:
                response_line = process.stdout.readline()
                if not response_line:
                    return process.wait()
                response = json.loads(response_line)
                if response.get("id") != request_id:
                    print(json.dumps(response, ensure_ascii=False), flush=True)
                    continue
                if request.get("method") == "tools/list":
                    result = response.get("result") or {}
                    tools = result.get("tools") or []
                    result["tools"] = [tool for tool in tools if tool.get("name") in ALLOWED_TOOLS]
                    response["result"] = result
                print(json.dumps(response, ensure_ascii=False), flush=True)
                break
    finally:
        process.terminate()
        try:
            process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            process.kill()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
