import React, { useEffect, useState, useCallback } from "react";
import {
  getDashboardStats,
  scanRepository,
  type DashboardStats,
} from "../bridge";
import { StatCard } from "../components/dashboard/StatCard";
import { CategoryBreakdown } from "../components/dashboard/CategoryBreakdown";
import { RecentProblems } from "../components/dashboard/RecentProblems";
import { ActivityHeatmap } from "../components/dashboard/ActivityHeatmap";
import { AddProblemModal } from "../components/dashboard/AddProblemModal";

interface HomeProps {
  repoPath?: string;
  onNavigateToRepo?: () => void;
}

export const Home: React.FC<HomeProps> = ({ repoPath }) => {
  const [stats, setStats] = useState<DashboardStats | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [rescanLoading, setRescanLoading] = useState<boolean>(false);
  const [isAddModalOpen, setIsAddModalOpen] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [actionNotice, setActionNotice] = useState<{
    type: "info" | "success" | "error";
    message: string;
  } | null>(null);

  const fetchStats = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const resp = await getDashboardStats(repoPath);
      if (resp.ok && resp.data && resp.data.success) {
        setStats(resp.data);
      } else {
        setError(resp.error || resp.data?.error || "Failed to load dashboard statistics.");
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setError(`Connection error: ${msg}`);
    } finally {
      setLoading(false);
    }
  }, [repoPath]);

  useEffect(() => {
    fetchStats();
  }, [fetchStats]);

  const handleRescan = async () => {
    setRescanLoading(true);
    setActionNotice({ type: "info", message: "Scanning repository for source files..." });
    try {
      const scanResp = await scanRepository(repoPath);
      if (scanResp.ok && scanResp.data && scanResp.data.success) {
        const total = scanResp.data.total_problems;
        setActionNotice({
          type: "success",
          message: `Rescan complete: ${total} problem${total === 1 ? "" : "s"} recognized.`,
        });
        // Refresh dashboard data
        const statsResp = await getDashboardStats(repoPath);
        if (statsResp.ok && statsResp.data && statsResp.data.success) {
          setStats(statsResp.data);
        }
      } else {
        setActionNotice({
          type: "error",
          message: `Rescan failed: ${scanResp.error || scanResp.data?.error || "Unknown error"}`,
        });
      }
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setActionNotice({ type: "error", message: `Rescan failed: ${msg}` });
    } finally {
      setRescanLoading(false);
    }
  };

  const handleAddProblem = () => {
    setIsAddModalOpen(true);
  };

  const handleAddProblemSuccess = async (_filePath: string, title: string, category: string) => {
    setActionNotice({
      type: "success",
      message: `Problem '${title}' created successfully in '${category}'. Refreshing dashboard...`,
    });
    // Refresh authoritative backend statistics
    await fetchStats();
  };

  if (loading && !stats) {
    return (
      <div className="home-loading-view">
        <div className="loading-spinner" />
        <p className="loading-text">Loading repository dashboard...</p>
      </div>
    );
  }

  if (error && !stats) {
    return (
      <div className="home-error-view">
        <div className="error-card">
          <div className="error-icon">⚠️</div>
          <h3 className="error-title">Unable to Load Dashboard</h3>
          <p className="error-message">{error}</p>
          <button className="primary-btn" onClick={fetchStats}>
            ↺ Retry Connection
          </button>
        </div>
      </div>
    );
  }

  const isRepoEmpty = !stats || stats.total_problems === 0;

  return (
    <div className="home-dashboard">
      {/* Top Bar: Title + Actions */}
      <div className="home-topbar">
        <div className="topbar-title-box">
          <h1 className="home-page-title">DSA Practice Overview</h1>
          <p className="home-page-subtitle">
            Real repository statistics and recorded activity
          </p>
        </div>

        <div className="topbar-actions">
          <button
            className="action-btn primary-action-btn"
            onClick={handleAddProblem}
            id="btn-add-problem"
          >
            + Add New Problem
          </button>
          <button
            className="action-btn secondary-action-btn"
            onClick={handleRescan}
            disabled={rescanLoading}
            id="btn-rescan"
          >
            {rescanLoading ? "Scanning..." : "↺ Rescan"}
          </button>
        </div>
      </div>

      {/* Action Notification Banner */}
      {actionNotice && (
        <div className={`action-notice notice-${actionNotice.type}`}>
          <span className="notice-text">{actionNotice.message}</span>
          <button
            className="notice-close-btn"
            onClick={() => setActionNotice(null)}
          >
            ✕
          </button>
        </div>
      )}

      {/* 4 Stat Cards Row */}
      <div className="stats-cards-grid">
        <StatCard
          title="Total Problems"
          value={stats?.total_problems ?? 0}
          subtitle="Recognized solutions"
          accentColor="var(--text-primary)"
        />
        <StatCard
          title="This Week"
          value={stats?.this_week ?? 0}
          subtitle="Mon → Sun activity"
          accentColor="var(--accent)"
        />
        <StatCard
          title="This Month"
          value={stats?.this_month ?? 0}
          subtitle="Current calendar month"
          accentColor="var(--accent-subtle)"
        />
        <StatCard
          title="Current Streak"
          value={`${stats?.current_streak ?? 0} ${
            stats?.current_streak === 1 ? "day" : "days"
          }`}
          subtitle={`Best: ${stats?.longest_streak ?? 0} ${
            stats?.longest_streak === 1 ? "day" : "days"
          }`}
          accentColor="var(--success)"
        />
      </div>

      {/* Main Content Area: Data vs Empty State */}
      {isRepoEmpty ? (
        <div className="empty-repo-card">
          <div className="empty-repo-icon">📂</div>
          <h2 className="empty-repo-title">No DSA problems found in repository</h2>
          <p className="empty-repo-description">
            Add your first DSA problem to start building your recorded repository
            activity and dashboard metrics.
          </p>
          <div className="empty-repo-actions">
            <button
              className="action-btn primary-action-btn"
              onClick={handleAddProblem}
            >
              + Add First Problem
            </button>
            <button
              className="action-btn secondary-action-btn"
              onClick={handleRescan}
            >
              ↺ Rescan Repository
            </button>
          </div>
        </div>
      ) : (
        <div className="dashboard-middle-row">
          <CategoryBreakdown
            categoryCounts={stats.category_counts || {}}
            mostPracticed={stats.most_practiced_categories || []}
            leastPracticed={stats.least_practiced_categories || []}
          />
          <RecentProblems problems={stats.recent_problems || []} />
        </div>
      )}

      {/* Bottom Panel: Activity Heatmap */}
      <ActivityHeatmap heatmapWeeks={stats?.heatmap_weeks || []} />

      {/* Add Problem Desktop Modal */}
      <AddProblemModal
        isOpen={isAddModalOpen}
        onClose={() => setIsAddModalOpen(false)}
        onSuccess={handleAddProblemSuccess}
        repoPath={repoPath}
      />
    </div>
  );
};
