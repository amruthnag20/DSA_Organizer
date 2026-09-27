import React from "react";

interface StatCardProps {
  title: string;
  value: number | string;
  subtitle?: string;
  secondaryValue?: string;
  accentColor?: string;
  icon?: string;
}

export const StatCard: React.FC<StatCardProps> = ({
  title,
  value,
  subtitle,
  secondaryValue,
  accentColor = "var(--text-primary)",
  icon,
}) => {
  return (
    <div className="stat-card">
      <div className="stat-card-header">
        <span className="stat-card-title">{title}</span>
        {icon && <span className="stat-card-icon">{icon}</span>}
      </div>
      <div className="stat-card-body">
        <span className="stat-card-value" style={{ color: accentColor }}>
          {value}
        </span>
        {secondaryValue && (
          <span className="stat-card-secondary">{secondaryValue}</span>
        )}
      </div>
      {subtitle && <div className="stat-card-subtitle">{subtitle}</div>}
    </div>
  );
};
