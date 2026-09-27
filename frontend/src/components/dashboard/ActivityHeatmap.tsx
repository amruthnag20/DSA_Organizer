import React, { useState } from "react";
import type { HeatmapDay } from "../../bridge";

interface ActivityHeatmapProps {
  heatmapWeeks: HeatmapDay[][];
}

export const ActivityHeatmap: React.FC<ActivityHeatmapProps> = ({ heatmapWeeks }) => {
  const [hoverText, setHoverText] = useState<string>(
    "Hover over any day square to view recorded activity."
  );

  const dayLabels = ["Mon", "", "Wed", "", "Fri", "", "Sun"];

  // Determine month header labels above week columns
  let lastMonth = "";
  const weekMonthLabels: (string | null)[] = (heatmapWeeks || []).map((week) => {
    if (!week || week.length === 0) return null;
    const firstDay = week[0];
    if (firstDay && firstDay.month_name && firstDay.month_name !== lastMonth) {
      lastMonth = firstDay.month_name;
      return firstDay.month_name;
    }
    return null;
  });

  return (
    <div className="dashboard-panel heatmap-panel">
      <div className="panel-header">
        <h3 className="panel-title">ACTIVITY HEATMAP — LAST 12 WEEKS</h3>
        <div className="heatmap-legend">
          <span className="legend-label">Less</span>
          <span className="legend-box level-0" title="0 problems" />
          <span className="legend-box level-1" title="1 problem" />
          <span className="legend-box level-2" title="2 problems" />
          <span className="legend-box level-3" title="3 problems" />
          <span className="legend-box level-4" title="4+ problems" />
          <span className="legend-label">More</span>
        </div>
      </div>

      <div className="heatmap-container">
        {/* Heatmap Grid */}
        <div className="heatmap-grid-wrapper">
          {/* Day of week labels on left */}
          <div className="heatmap-day-labels">
            <div className="month-header-spacer" />
            {dayLabels.map((lbl, idx) => (
              <div key={idx} className="day-label">
                {lbl}
              </div>
            ))}
          </div>

          {/* 12 Week Columns */}
          <div className="heatmap-weeks">
            {/* Month labels row */}
            <div className="heatmap-month-row">
              {weekMonthLabels.map((month, idx) => (
                <div key={idx} className="month-label-col">
                  {month ? <span className="month-text">{month}</span> : null}
                </div>
              ))}
            </div>

            {/* Columns of 7 days */}
            <div className="heatmap-columns-row">
              {(heatmapWeeks || []).map((week, wIdx) => (
                <div key={wIdx} className="heatmap-column">
                  {(week || []).map((day, dIdx) => {
                    const levelClass = `level-${Math.min(4, Math.max(0, day.level || 0))}`;
                    const todayClass = day.is_today ? "is-today" : "";
                    const futureClass = day.is_future ? "is-future" : "";

                    return (
                      <div
                        key={day.date || `${wIdx}-${dIdx}`}
                        className={`heatmap-cell ${levelClass} ${todayClass} ${futureClass}`}
                        onMouseEnter={() => {
                          const count = day.count || 0;
                          const problemWord = count === 1 ? "problem" : "problems";
                          const dateDisplay = day.formatted_date || day.date;
                          setHoverText(`${count} ${problemWord} on ${dateDisplay}${day.is_today ? " (Today)" : ""}`);
                        }}
                        onMouseLeave={() => {
                          setHoverText("Hover over any day square to view recorded activity.");
                        }}
                      />
                    );
                  })}
                </div>
              ))}
            </div>
          </div>
        </div>

        {/* Hover / Status Text */}
        <div className="heatmap-hover-bar">
          <span className="hover-icon">ⓘ</span>
          <span className="hover-message">{hoverText}</span>
        </div>
      </div>
    </div>
  );
};
