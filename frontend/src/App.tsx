import React, { useEffect, useState } from "react";
import { loadConfig, type ProjectConfig } from "./bridge";
import { Home } from "./pages/Home";
import "./App.css";

type ActiveTab = "home" | "search" | "repo";

export const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<ActiveTab>("home");
  const [config, setConfig] = useState<ProjectConfig | null>(null);
  const [repoPathDisplay, setRepoPathDisplay] = useState<string>("Loading...");
  const [notice, setNotice] = useState<string | null>(null);

  useEffect(() => {
    async function init() {
      try {
        const resp = await loadConfig();
        if (resp.ok && resp.data?.success && resp.data.config) {
          const cfg = resp.data.config;
          setConfig(cfg);
          const fullPath = cfg.repository_path || cfg.repository || "Not configured";
          const folderName = fullPath.split(/[\\/]/).filter(Boolean).pop() || fullPath;
          setRepoPathDisplay(folderName);
        } else {
          setRepoPathDisplay("No repository configured");
        }
      } catch {
        setRepoPathDisplay("Connection error");
      }
    }
    init();
  }, []);

  const handleNavClick = (tab: ActiveTab) => {
    if (tab === "home") {
      setActiveTab("home");
    } else if (tab === "search") {
      setNotice("Search migration is scheduled for Phase 3. Use the legacy interface in the meantime.");
    } else if (tab === "repo") {
      setNotice("Repository & Git migration is scheduled for Phase 4. Use the legacy interface in the meantime.");
    }
  };

  return (
    <div className="desktop-layout">
      {/* ── 1. PERSISTENT DESKTOP SIDEBAR ── */}
      <aside className="desktop-sidebar">
        <div className="sidebar-brand">
          <div className="brand-title">DSA ORGANIZER</div>
          <div className="brand-subtitle">DESKTOP UTILITY</div>
        </div>

        <nav className="sidebar-nav">
          <button
            className={`nav-item ${activeTab === "home" ? "active" : ""}`}
            onClick={() => handleNavClick("home")}
            id="nav-home"
          >
            <span className="nav-icon">⌂</span>
            <span className="nav-text">Home</span>
          </button>

          <button
            className={`nav-item ${activeTab === "search" ? "active" : ""}`}
            onClick={() => handleNavClick("search")}
            id="nav-search"
            title="Scheduled for Phase 3"
          >
            <span className="nav-icon">🔎</span>
            <span className="nav-text">Search</span>
            <span className="nav-badge">Phase 3</span>
          </button>

          <button
            className={`nav-item ${activeTab === "repo" ? "active" : ""}`}
            onClick={() => handleNavClick("repo")}
            id="nav-repo"
            title="Scheduled for Phase 4"
          >
            <span className="nav-icon">⚙</span>
            <span className="nav-text">Repository & Git</span>
            <span className="nav-badge">Phase 4</span>
          </button>
        </nav>

        {/* Sidebar Footer: Repository Indicator */}
        <div className="sidebar-footer">
          <div className="repo-indicator" title={config?.repository_path || config?.repository || ""}>
            <span className="repo-dot" />
            <div className="repo-info">
              <span className="repo-label">REPOSITORY</span>
              <span className="repo-name">{repoPathDisplay}</span>
            </div>
          </div>
        </div>
      </aside>

      {/* ── 2. MAIN APPLICATION CONTENT ── */}
      <main className="desktop-main">
        {notice && (
          <div className="desktop-global-notice">
            <span>{notice}</span>
            <button className="notice-dismiss-btn" onClick={() => setNotice(null)}>
              ✕
            </button>
          </div>
        )}

        <Home
          repoPath={config?.repository_path || config?.repository}
          onNavigateToRepo={() => handleNavClick("repo")}
        />
      </main>
    </div>
  );
};

export default App;
