import React from "react";
import type { ProblemRecord } from "../../bridge";

interface RecentProblemsProps {
  problems: ProblemRecord[];
}

export const RecentProblems: React.FC<RecentProblemsProps> = ({ problems }) => {
  return (
    <div className="dashboard-panel recent-panel">
      <div className="panel-header">
        <h3 className="panel-title">RECENT PROBLEMS</h3>
        <span className="panel-badge">{problems.length} Recorded</span>
      </div>

      <div className="recent-table-wrapper">
        <table className="compact-table recent-table">
          <thead>
            <tr>
              <th style={{ textAlign: "left" }}>Title</th>
              <th style={{ textAlign: "left", width: "130px" }}>Category</th>
              <th style={{ textAlign: "left", width: "110px" }}>Platform</th>
              <th style={{ textAlign: "left", width: "120px" }}>Date</th>
            </tr>
          </thead>
          <tbody>
            {problems.length > 0 ? (
              problems.map((p, idx) => (
                <tr key={`${p.file_path || p.rel_path}-${idx}`} className="recent-row">
                  <td className="title-cell" title={p.title || "Untitled"}>
                    <div className="problem-title-box">
                      <span className="problem-title">{p.title || "Untitled"}</span>
                      {p.language && (
                        <span className="lang-badge">{p.language}</span>
                      )}
                    </div>
                  </td>
                  <td className="category-cell">
                    <span className="cat-badge">{p.category || "—"}</span>
                  </td>
                  <td className="platform-cell">
                    <span className="platform-name">{p.platform || "—"}</span>
                  </td>
                  <td className="date-cell">
                    <span className="date-text" title={p.formatted_date || p.added_date || ""}>
                      {p.added_date || "—"}
                    </span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={4} className="empty-cell">
                  No recent problems recorded
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
