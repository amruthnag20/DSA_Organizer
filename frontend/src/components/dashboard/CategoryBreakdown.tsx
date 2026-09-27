import React from "react";

interface CategoryBreakdownProps {
  categoryCounts: Record<string, number>;
  mostPracticed: [string, number][];
  leastPracticed: [string, number][];
}

export const CategoryBreakdown: React.FC<CategoryBreakdownProps> = ({
  categoryCounts,
  mostPracticed,
  leastPracticed,
}) => {
  // Sort all categories: count descending, then alphabetical
  const allCategories = Object.entries(categoryCounts).sort((a, b) => {
    if (b[1] !== a[1]) {
      return b[1] - a[1];
    }
    return a[0].localeCompare(b[0]);
  });

  return (
    <div className="dashboard-panel category-panel">
      <div className="panel-header">
        <h3 className="panel-title">CATEGORIES</h3>
        <span className="panel-badge">{allCategories.length} Categories</span>
      </div>

      {/* Highlights Box */}
      <div className="category-highlights">
        <div className="highlight-section">
          <div className="highlight-label">Most Practiced</div>
          <div className="highlight-tags">
            {mostPracticed.length > 0 ? (
              mostPracticed.map(([cat, count]) => (
                <div key={cat} className="category-tag most-tag">
                  <span className="cat-name">{cat}</span>
                  <span className="cat-count">{count}</span>
                </div>
              ))
            ) : (
              <span className="empty-subtext">No categories recorded</span>
            )}
          </div>
        </div>

        <div className="highlight-section">
          <div className="highlight-label">Less Practiced</div>
          <div className="highlight-tags">
            {leastPracticed.length > 0 ? (
              leastPracticed.map(([cat, count]) => (
                <div key={cat} className="category-tag least-tag">
                  <span className="cat-name">{cat}</span>
                  <span className="cat-count">{count}</span>
                </div>
              ))
            ) : (
              <span className="empty-subtext">No categories recorded</span>
            )}
          </div>
        </div>
      </div>

      {/* All Categories Table */}
      <div className="panel-subheader">All Categories Breakdown</div>
      <div className="category-table-wrapper">
        <table className="compact-table category-table">
          <thead>
            <tr>
              <th style={{ textAlign: "left" }}>Primary Category</th>
              <th style={{ textAlign: "right", width: "70px" }}>Count</th>
            </tr>
          </thead>
          <tbody>
            {allCategories.length > 0 ? (
              allCategories.map(([cat, count]) => (
                <tr key={cat}>
                  <td className="category-cell">{cat}</td>
                  <td className="count-cell" style={{ textAlign: "right" }}>
                    <span className="count-pill">{count}</span>
                  </td>
                </tr>
              ))
            ) : (
              <tr>
                <td colSpan={2} className="empty-cell">
                  No category data available
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
};
