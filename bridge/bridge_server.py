"""
bridge_server.py — Long-lived Python process that exposes engine/backend.py
functions via a JSON-RPC-style protocol over stdin/stdout.

Protocol:
  - Reads one JSON object per line from stdin
  - Each request: {"id": <string>, "cmd": <string>, "args": <object>}
  - Each response: {"id": <string>, "ok": <bool>, "data": <any>, "error": <string|null>}
  - Writes one JSON response per line to stdout
  - Uses stderr for debug logging (never stdout)

Lifecycle:
  - Runs until stdin is closed or a "shutdown" command is received
  - Tauri spawns this process on app startup, kills on app exit
"""

import json
import sys
import os
import traceback

# Ensure the project root (parent of bridge/) is on sys.path
# so that `engine.backend` can be imported regardless of cwd.
BRIDGE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(BRIDGE_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from engine import backend  # noqa: E402


def log(msg: str) -> None:
    """Write debug messages to stderr (never stdout — that's the data channel)."""
    sys.stderr.write(f"[bridge] {msg}\n")
    sys.stderr.flush()


def send_response(response: dict) -> None:
    """Write a single JSON response line to stdout."""
    line = json.dumps(response, default=str)
    sys.stdout.write(line + "\n")
    sys.stdout.flush()


# ---------------------------------------------------------------------------
# Command handlers — domain-level, not screen-specific
# ---------------------------------------------------------------------------

def handle_ping(args: dict) -> dict:
    """Health check."""
    return {"status": "ok", "message": "Bridge is alive"}


def handle_load_config(args: dict) -> dict:
    """Load project.json configuration."""
    config, error = backend.load_config()
    if error:
        return {"success": False, "error": error, "config": None}
    return {"success": True, "error": None, "config": config}


def handle_validate_repository(args: dict) -> dict:
    """Validate whether the configured repository path is accessible."""
    repo_path = args.get("repo_path")
    if not repo_path:
        # Attempt to load from config
        config, err = backend.load_config()
        if err or not config:
            return {"valid": False, "message": err or "No configuration found"}
        repo_path = config.get("repository_path") or config.get("repository")
    
    is_valid, message = backend.validate_repository(repo_path)
    return {"valid": is_valid, "message": message}


def handle_scan_repository(args: dict) -> dict:
    """Scan the repository for all problem files and metadata."""
    repo_path = args.get("repo_path")
    if not repo_path:
        config, err = backend.load_config()
        if err or not config:
            return {"success": False, "error": err or "No configuration found"}
        repo_path = config.get("repository_path") or config.get("repository")
    
    result = backend.scan_repository(repo_path)
    return result


def handle_get_dashboard_stats(args: dict) -> dict:
    """Get dashboard statistics from the repository."""
    repo_path = args.get("repo_path")
    if not repo_path:
        config, err = backend.load_config()
        if err or not config:
            return {"success": False, "error": err or "No configuration found"}
        repo_path = config.get("repository_path") or config.get("repository")
    
    result = backend.get_dashboard_stats(repo_path)
    return result


def handle_get_categories(args: dict) -> dict:
    """Get all available categories (built-in + custom)."""
    categories = backend.get_categories()
    return {"categories": categories}


def handle_get_all_platforms(args: dict) -> dict:
    """Get all available platforms (built-in + custom)."""
    platforms = backend.get_all_platforms()
    return {"platforms": platforms}


def handle_get_all_tags(args: dict) -> dict:
    """Get all available tags (built-in + custom)."""
    tags = backend.get_all_tags()
    return {"tags": tags}


def handle_ensure_directories(args: dict) -> dict:
    """Ensure core project directories exist."""
    ok, msg = backend.ensure_project_directories()
    return {"success": ok, "message": msg}


def handle_verify_git(args: dict) -> dict:
    """Check Git availability and repository status."""
    repo_path = args.get("repo_path")
    if not repo_path:
        config, err = backend.load_config()
        if err or not config:
            return {"success": False, "error": err or "No configuration found"}
        repo_path = config.get("repository_path") or config.get("repository")
    
    git_ok, git_msg = backend.is_git_available()
    if not git_ok:
        return {"git_available": False, "message": git_msg}
    
    result = backend.verify_git_configuration(repo_path)
    result["git_available"] = True
    return result


# ---------------------------------------------------------------------------
# Command dispatch table
# ---------------------------------------------------------------------------

COMMANDS = {
    "ping":                 handle_ping,
    "load_config":          handle_load_config,
    "validate_repository":  handle_validate_repository,
    "scan_repository":      handle_scan_repository,
    "get_dashboard_stats":  handle_get_dashboard_stats,
    "get_categories":       handle_get_categories,
    "get_all_platforms":    handle_get_all_platforms,
    "get_all_tags":         handle_get_all_tags,
    "ensure_directories":   handle_ensure_directories,
    "verify_git":           handle_verify_git,
}


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def process_request(request: dict) -> dict:
    """Dispatch a single request and return a response dict."""
    req_id = request.get("id", "unknown")
    cmd = request.get("cmd")
    args = request.get("args", {})

    if not cmd:
        return {"id": req_id, "ok": False, "data": None, "error": "Missing 'cmd' field"}

    if cmd == "shutdown":
        return {"id": req_id, "ok": True, "data": {"status": "shutting_down"}, "error": None}

    handler = COMMANDS.get(cmd)
    if not handler:
        return {
            "id": req_id, "ok": False, "data": None,
            "error": f"Unknown command: {cmd}. Available: {list(COMMANDS.keys())}"
        }

    try:
        data = handler(args)
        return {"id": req_id, "ok": True, "data": data, "error": None}
    except Exception as exc:
        log(f"Error handling '{cmd}': {traceback.format_exc()}")
        return {"id": req_id, "ok": False, "data": None, "error": str(exc)}


def main() -> None:
    """Run the bridge server: read JSON lines from stdin, dispatch, respond on stdout."""
    log("Bridge server starting...")
    log(f"Project root: {PROJECT_ROOT}")
    log(f"Python: {sys.executable}")

    # Signal readiness
    send_response({"id": "__init__", "ok": True, "data": {"status": "ready"}, "error": None})

    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue

        try:
            request = json.loads(line)
        except json.JSONDecodeError as exc:
            send_response({
                "id": "unknown", "ok": False, "data": None,
                "error": f"Invalid JSON: {exc}"
            })
            continue

        response = process_request(request)
        send_response(response)

        # Check for shutdown
        if request.get("cmd") == "shutdown":
            log("Shutdown requested. Exiting.")
            break

    log("Bridge server exiting.")


if __name__ == "__main__":
    main()
