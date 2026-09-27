import { useEffect, useState } from "react";
import {
  ping,
  loadConfig,
  validateRepository,
  scanRepository,
  type ProjectConfig,
  type BridgeResponse,
  type ScanResult,
} from "./bridge";
import "./App.css";

/**
 * Phase 1 — Minimal application shell.
 *
 * This is intentionally plain. It exists only to prove the
 * React → Tauri → Python → engine pipeline works end-to-end.
 *
 * Visual redesign happens in later phases.
 */

type ConnectionStatus = "connecting" | "connected" | "error";

interface StatusEntry {
  label: string;
  value: string;
  ok: boolean;
}

function App() {
  const [connectionStatus, setConnectionStatus] =
    useState<ConnectionStatus>("connecting");
  const [statusEntries, setStatusEntries] = useState<StatusEntry[]>([]);
  const [config, setConfig] = useState<ProjectConfig | null>(null);
  const [scanResult, setScanResult] = useState<ScanResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  // On mount: run the connection check sequence
  useEffect(() => {
    runStartupChecks();
  }, []);

  async function runStartupChecks() {
    const entries: StatusEntry[] = [];
    setLoading(true);

    try {
      // 1. Ping the bridge
      const pingResp = await ping();
      if (pingResp.ok) {
        setConnectionStatus("connected");
        entries.push({
          label: "Bridge Connection",
          value: "Connected",
          ok: true,
        });
      } else {
        setConnectionStatus("error");
        entries.push({
          label: "Bridge Connection",
          value: pingResp.error || "Failed",
          ok: false,
        });
        setStatusEntries(entries);
        setLoading(false);
        return;
      }

      // 2. Load config
      const configResp = await loadConfig();
      if (configResp.ok && configResp.data?.success && configResp.data.config) {
        const cfg = configResp.data.config;
        setConfig(cfg);
        const repoPath = cfg.repository_path || cfg.repository || "Not set";
        entries.push({
          label: "Configuration",
          value: "Loaded",
          ok: true,
        });
        entries.push({
          label: "Repository Path",
          value: repoPath,
          ok: true,
        });
      } else {
        entries.push({
          label: "Configuration",
          value: configResp.data?.error || configResp.error || "Failed",
          ok: false,
        });
      }

      // 3. Validate repository
      const valResp = await validateRepository();
      entries.push({
        label: "Repository Validation",
        value: valResp.data?.message || "Unknown",
        ok: valResp.ok && (valResp.data?.valid ?? false),
      });

      setStatusEntries(entries);
    } catch (err) {
      setConnectionStatus("error");
      setError(err instanceof Error ? err.message : String(err));
      entries.push({
        label: "Bridge Connection",
        value: "Failed to connect",
        ok: false,
      });
      setStatusEntries(entries);
    } finally {
      setLoading(false);
    }
  }

  async function handleScan() {
    setLoading(true);
    setScanResult(null);
    try {
      const resp: BridgeResponse<ScanResult> = await scanRepository();
      if (resp.ok && resp.data) {
        setScanResult(resp.data);
      } else {
        setError(resp.error || "Scan failed");
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : String(err));
    } finally {
      setLoading(false);
    }
  }

  const statusColor =
    connectionStatus === "connected"
      ? "#4caf50"
      : connectionStatus === "error"
      ? "#f44336"
      : "#ff9800";

  return (
    <div className="app-shell">
      <header className="app-header">
        <h1>DSA Organizer</h1>
        <div className="connection-badge" style={{ backgroundColor: statusColor }}>
          {connectionStatus === "connecting"
            ? "⏳ Connecting..."
            : connectionStatus === "connected"
            ? "✓ Bridge Connected"
            : "✗ Bridge Error"}
        </div>
      </header>

      <main className="app-main">
        <section className="status-section">
          <h2>System Status</h2>
          {loading && <p className="loading-text">Running checks...</p>}

          {statusEntries.length > 0 && (
            <table className="status-table">
              <thead>
                <tr>
                  <th>Check</th>
                  <th>Status</th>
                  <th>Result</th>
                </tr>
              </thead>
              <tbody>
                {statusEntries.map((entry, i) => (
                  <tr key={i}>
                    <td>{entry.label}</td>
                    <td>
                      <span className={entry.ok ? "status-ok" : "status-fail"}>
                        {entry.ok ? "✓" : "✗"}
                      </span>
                    </td>
                    <td className="status-value">{entry.value}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}

          {error && (
            <div className="error-box">
              <strong>Error:</strong> {error}
            </div>
          )}
        </section>

        {connectionStatus === "connected" && (
          <section className="actions-section">
            <h2>Actions</h2>
            <button
              onClick={handleScan}
              disabled={loading}
              className="action-btn"
            >
              {loading ? "Scanning..." : "Scan Repository"}
            </button>
            <button
              onClick={runStartupChecks}
              disabled={loading}
              className="action-btn"
            >
              Re-check Connection
            </button>
          </section>
        )}

        {scanResult && (
          <section className="scan-section">
            <h2>Scan Results</h2>
            <div className="scan-stats">
              <div className="stat-card">
                <span className="stat-value">{scanResult.total_problems}</span>
                <span className="stat-label">Total Problems</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{scanResult.complete_count}</span>
                <span className="stat-label">Complete</span>
              </div>
              <div className="stat-card">
                <span className="stat-value">{scanResult.incomplete_count}</span>
                <span className="stat-label">Incomplete</span>
              </div>
              {scanResult.mismatch_count > 0 && (
                <div className="stat-card stat-warning">
                  <span className="stat-value">{scanResult.mismatch_count}</span>
                  <span className="stat-label">Mismatched</span>
                </div>
              )}
            </div>

            {scanResult.problems.length > 0 && (
              <table className="problems-table">
                <thead>
                  <tr>
                    <th>Title</th>
                    <th>Category</th>
                    <th>Platform</th>
                    <th>Language</th>
                    <th>Status</th>
                  </tr>
                </thead>
                <tbody>
                  {scanResult.problems.map((p, i) => (
                    <tr key={i}>
                      <td>{p.title}</td>
                      <td>{p.folder_category}</td>
                      <td>{p.platform || "—"}</td>
                      <td>{p.language}</td>
                      <td>
                        <span
                          className={
                            p.status === "complete"
                              ? "status-ok"
                              : p.status === "incomplete"
                              ? "status-warn"
                              : "status-fail"
                          }
                        >
                          {p.status}
                        </span>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </section>
        )}
      </main>

      <footer className="app-footer">
        <span>Phase 1 — Architecture Migration Shell</span>
        {config && (
          <span className="footer-repo">
            📁 {config.repository_path || config.repository || "No repo"}
          </span>
        )}
      </footer>
    </div>
  );
}

export default App;
