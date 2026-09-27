"""
test_bridge.py — Integration tests for the Python bridge server.

Tests the bridge subprocess protocol directly (no Tauri needed).
Validates that the bridge correctly dispatches domain-level commands
to engine/backend.py and returns properly structured JSON responses.
"""

import json
import os
import subprocess
import sys
import time
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent
BRIDGE_SCRIPT = PROJECT_ROOT / "bridge" / "bridge_server.py"


class BridgeProcess:
    """Helper to manage a bridge server subprocess for testing."""

    def __init__(self):
        self.process = None

    def start(self):
        """Start the bridge server subprocess."""
        self.process = subprocess.Popen(
            [sys.executable, str(BRIDGE_SCRIPT)],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=str(PROJECT_ROOT),
            text=True,
            bufsize=1,  # Line buffered
        )
        # Read the readiness signal
        init_line = self.process.stdout.readline()
        init_resp = json.loads(init_line)
        assert init_resp["id"] == "__init__"
        assert init_resp["ok"] is True
        assert init_resp["data"]["status"] == "ready"
        return init_resp

    def send(self, cmd: str, args: dict = None, req_id: str = None) -> dict:
        """Send a command and read the response."""
        if req_id is None:
            req_id = f"test-{cmd}"
        request = {"id": req_id, "cmd": cmd, "args": args or {}}
        line = json.dumps(request) + "\n"
        self.process.stdin.write(line)
        self.process.stdin.flush()
        response_line = self.process.stdout.readline()
        if not response_line:
            raise RuntimeError("Bridge process returned empty response (possibly crashed)")
        return json.loads(response_line)

    def stop(self):
        """Gracefully stop the bridge server."""
        if self.process and self.process.poll() is None:
            try:
                resp = self.send("shutdown")
            except Exception:
                pass
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait()

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()


# ============================================================================
# Tests
# ============================================================================

class TestBridgeProtocol:
    """Test the bridge JSON-RPC protocol basics."""

    def test_bridge_starts_and_signals_ready(self):
        """Bridge process starts and sends readiness signal."""
        with BridgeProcess() as bridge:
            # If we get here, the __init__ response was valid
            assert bridge.process.poll() is None  # Still running

    def test_ping(self):
        """Ping command returns ok status."""
        with BridgeProcess() as bridge:
            resp = bridge.send("ping")
            assert resp["ok"] is True
            assert resp["data"]["status"] == "ok"
            assert resp["id"] == "test-ping"

    def test_unknown_command(self):
        """Unknown command returns error with available commands list."""
        with BridgeProcess() as bridge:
            resp = bridge.send("nonexistent_command_xyz")
            assert resp["ok"] is False
            assert "Unknown command" in resp["error"]
            assert "nonexistent_command_xyz" in resp["error"]

    def test_missing_cmd_field(self):
        """Request without cmd field returns error."""
        with BridgeProcess() as bridge:
            request = {"id": "test-no-cmd", "args": {}}
            line = json.dumps(request) + "\n"
            bridge.process.stdin.write(line)
            bridge.process.stdin.flush()
            response_line = bridge.process.stdout.readline()
            resp = json.loads(response_line)
            assert resp["ok"] is False
            assert "Missing 'cmd'" in resp["error"]

    def test_invalid_json(self):
        """Invalid JSON input returns error without crashing."""
        with BridgeProcess() as bridge:
            bridge.process.stdin.write("this is not json\n")
            bridge.process.stdin.flush()
            response_line = bridge.process.stdout.readline()
            resp = json.loads(response_line)
            assert resp["ok"] is False
            assert "Invalid JSON" in resp["error"]
            # Bridge should still be alive
            resp2 = bridge.send("ping")
            assert resp2["ok"] is True

    def test_shutdown_command(self):
        """Shutdown command causes graceful exit."""
        with BridgeProcess() as bridge:
            resp = bridge.send("shutdown")
            assert resp["ok"] is True
            assert resp["data"]["status"] == "shutting_down"
            # Process should exit shortly
            bridge.process.wait(timeout=5)
            assert bridge.process.returncode == 0

    def test_custom_request_id_preserved(self):
        """Response preserves the request id from the caller."""
        with BridgeProcess() as bridge:
            resp = bridge.send("ping", req_id="my-custom-id-42")
            assert resp["id"] == "my-custom-id-42"

    def test_multiple_commands_sequential(self):
        """Multiple commands can be sent sequentially over the same connection."""
        with BridgeProcess() as bridge:
            r1 = bridge.send("ping", req_id="seq-1")
            r2 = bridge.send("ping", req_id="seq-2")
            r3 = bridge.send("ping", req_id="seq-3")
            assert r1["ok"] and r2["ok"] and r3["ok"]
            assert r1["id"] == "seq-1"
            assert r2["id"] == "seq-2"
            assert r3["id"] == "seq-3"


class TestBridgeDomainCommands:
    """Test domain-level commands that call engine/backend.py."""

    def test_load_config(self):
        """load_config returns the project.json configuration."""
        with BridgeProcess() as bridge:
            resp = bridge.send("load_config")
            assert resp["ok"] is True
            data = resp["data"]
            assert data["success"] is True
            assert data["config"] is not None
            config = data["config"]
            # project.json should have repository_path
            assert "repository_path" in config or "repository" in config

    def test_validate_repository(self):
        """validate_repository checks the configured repo path."""
        with BridgeProcess() as bridge:
            # First load config to get the repo path
            config_resp = bridge.send("load_config")
            config = config_resp["data"]["config"]
            repo_path = config.get("repository_path") or config.get("repository")

            resp = bridge.send("validate_repository", {"repo_path": repo_path})
            assert resp["ok"] is True
            # Whether valid depends on if the repo actually exists
            assert "valid" in resp["data"]
            assert "message" in resp["data"]

    def test_validate_repository_auto_from_config(self):
        """validate_repository loads repo_path from config when not provided."""
        with BridgeProcess() as bridge:
            resp = bridge.send("validate_repository", {})
            assert resp["ok"] is True
            assert "valid" in resp["data"]

    def test_validate_repository_invalid_path(self):
        """validate_repository returns invalid for nonexistent path."""
        with BridgeProcess() as bridge:
            resp = bridge.send("validate_repository", {"repo_path": "Z:\\nonexistent\\path\\xyz"})
            assert resp["ok"] is True  # Command succeeded
            assert resp["data"]["valid"] is False

    def test_scan_repository(self):
        """scan_repository returns structured scan results."""
        with BridgeProcess() as bridge:
            resp = bridge.send("scan_repository")
            assert resp["ok"] is True
            data = resp["data"]
            # Scan returns these standard fields
            assert "total_problems" in data
            assert "problems" in data
            assert isinstance(data["problems"], list)

    def test_get_dashboard_stats(self):
        """get_dashboard_stats returns dashboard statistics."""
        with BridgeProcess() as bridge:
            resp = bridge.send("get_dashboard_stats")
            assert resp["ok"] is True
            data = resp["data"]
            assert "total_problems" in data

    def test_get_categories(self):
        """get_categories returns list of available categories."""
        with BridgeProcess() as bridge:
            resp = bridge.send("get_categories")
            assert resp["ok"] is True
            data = resp["data"]
            assert "categories" in data
            assert isinstance(data["categories"], list)
            assert len(data["categories"]) > 0
            # Should contain default categories
            assert "Arrays" in data["categories"]

    def test_get_all_platforms(self):
        """get_all_platforms returns list of available platforms."""
        with BridgeProcess() as bridge:
            resp = bridge.send("get_all_platforms")
            assert resp["ok"] is True
            data = resp["data"]
            assert "platforms" in data
            assert isinstance(data["platforms"], list)
            assert "LeetCode" in data["platforms"]

    def test_get_all_tags(self):
        """get_all_tags returns list of available tags."""
        with BridgeProcess() as bridge:
            resp = bridge.send("get_all_tags")
            assert resp["ok"] is True
            data = resp["data"]
            assert "tags" in data
            assert isinstance(data["tags"], list)
            assert "Interview" in data["tags"]

    def test_ensure_directories(self):
        """ensure_directories verifies core project structure."""
        with BridgeProcess() as bridge:
            resp = bridge.send("ensure_directories")
            assert resp["ok"] is True
            assert resp["data"]["success"] is True

    def test_verify_git(self):
        """verify_git checks Git availability and configuration."""
        with BridgeProcess() as bridge:
            resp = bridge.send("verify_git")
            assert resp["ok"] is True
            data = resp["data"]
            assert "git_available" in data


class TestBridgeResponseFormat:
    """Verify the response envelope is always correct."""

    def test_success_response_has_all_fields(self):
        """Successful response contains id, ok, data, error=None."""
        with BridgeProcess() as bridge:
            resp = bridge.send("ping", req_id="format-test")
            assert "id" in resp
            assert "ok" in resp
            assert "data" in resp
            assert "error" in resp
            assert resp["error"] is None

    def test_error_response_has_all_fields(self):
        """Error response contains id, ok=False, data=None, error string."""
        with BridgeProcess() as bridge:
            resp = bridge.send("unknown_cmd_xyz", req_id="err-format")
            assert resp["id"] == "err-format"
            assert resp["ok"] is False
            assert resp["data"] is None
            assert isinstance(resp["error"], str)
            assert len(resp["error"]) > 0
